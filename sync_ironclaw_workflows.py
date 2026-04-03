#!/usr/bin/env python3
"""Sync ironclaw jobs and routines into OpenSpace's workflow board.

OpenSpace discovers workflows by scanning WORKFLOW_ROOTS for directories
that contain a ``metadata.json`` or ``traj.jsonl`` file (up to 6 levels deep).
This script writes those files into ``logs/recordings/ironclaw-jobs/`` and
``logs/recordings/ironclaw-routines/`` -- which are volume-mounted into the
cubecloud-dashboard container at ``/app/logs/recordings/``.

The dashboard immediately picks up new directories on the next page load.
No OpenSpace DB writes are needed.

Usage:
    python sync_ironclaw_workflows.py              # sync all completed/failed jobs + all routines
    python sync_ironclaw_workflows.py --watch      # continuous mode: re-sync every 60 s
    python sync_ironclaw_workflows.py --dry-run    # preview only
    python sync_ironclaw_workflows.py --force      # overwrite already-synced entries
    python sync_ironclaw_workflows.py --remove     # delete all synced dirs

Environment:
    IRONCLAW_DB_URL   postgres connection string (default: from .env in ironclaw/)
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
OPENSPACE_ROOT = Path(__file__).resolve().parent       # OpenSpace/
IRONCLAW_ROOT  = OPENSPACE_ROOT.parent / "ironclaw"   # ironclaw/

# Volume-mounted path: OpenSpace/logs/ → container /app/logs/
LOGS_ROOT     = OPENSPACE_ROOT / "logs" / "recordings"
JOBS_DIR      = LOGS_ROOT / "ironclaw-jobs"
ROUTINES_DIR  = LOGS_ROOT / "ironclaw-routines"

# Marker file so we can identify dirs we created (for --remove)
MARKER_FILE   = ".ironclaw_sync"

# Default DB URL (reads from ironclaw/.env if not set in env)
_DEFAULT_DB_URL = "postgres://ironclaw:ironclaw@localhost/ironclaw"


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def _load_db_url() -> str:
    url = os.environ.get("IRONCLAW_DB_URL")
    if url:
        return url
    env_file = IRONCLAW_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\s*DATABASE_URL\s*=\s*(.+)$", line)
            if m:
                return m.group(1).strip()
    return _DEFAULT_DB_URL


@contextmanager
def _pg(db_url: str) -> Generator:
    """Minimal psycopg2 connection context manager."""
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary", file=sys.stderr)
        sys.exit(1)
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            yield cur
    finally:
        conn.close()


def _fetch_jobs(cur) -> List[Dict]:
    cur.execute("""
        SELECT
            j.id::text            AS id,
            j.title,
            j.description,
            j.status,
            j.category,
            j.source,
            j.success,
            j.failure_reason,
            j.actual_time_secs,
            j.estimated_time_secs,
            j.actual_cost,
            j.repair_attempts,
            j.job_mode,
            j.total_tokens_used,
            j.created_at          AT TIME ZONE 'UTC' AS created_at,
            j.started_at          AT TIME ZONE 'UTC' AS started_at,
            j.completed_at        AT TIME ZONE 'UTC' AS completed_at,
            j.conversation_id::text AS conversation_id
        FROM agent_jobs j
        WHERE j.status IN ('completed', 'failed', 'submitted', 'accepted')
        ORDER BY j.created_at DESC
    """)
    return [dict(r) for r in cur.fetchall()]


def _fetch_job_actions(cur, job_id: str) -> List[Dict]:
    cur.execute("""
        SELECT
            sequence_num,
            tool_name,
            input::text           AS input_json,
            output_sanitized::text AS output_json,
            cost,
            duration_ms,
            success,
            error_message,
            created_at            AT TIME ZONE 'UTC' AS created_at
        FROM job_actions
        WHERE job_id = %s
        ORDER BY sequence_num
    """, (job_id,))
    return [dict(r) for r in cur.fetchall()]


def _fetch_routines(cur) -> List[Dict]:
    cur.execute("""
        SELECT
            r.id::text          AS id,
            r.name,
            r.description,
            r.user_id,
            r.enabled,
            r.trigger_type,
            r.trigger_config::text AS trigger_config_json,
            r.action_type,
            r.action_config::text  AS action_config_json,
            r.cooldown_secs,
            r.last_run_at       AT TIME ZONE 'UTC' AS last_run_at,
            r.next_fire_at      AT TIME ZONE 'UTC' AS next_fire_at,
            r.run_count,
            r.consecutive_failures,
            r.created_at        AT TIME ZONE 'UTC' AS created_at,
            r.updated_at        AT TIME ZONE 'UTC' AS updated_at
        FROM routines r
        ORDER BY r.created_at DESC
    """)
    return [dict(r) for r in cur.fetchall()]


def _fetch_routine_runs(cur, routine_id: str) -> List[Dict]:
    cur.execute("""
        SELECT
            id::text            AS id,
            trigger_type,
            trigger_detail,
            started_at          AT TIME ZONE 'UTC' AS started_at,
            completed_at        AT TIME ZONE 'UTC' AS completed_at,
            status,
            result_summary,
            tokens_used,
            job_id::text        AS job_id
        FROM routine_runs
        WHERE routine_id = %s
        ORDER BY started_at DESC
        LIMIT 50
    """, (routine_id,))
    return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------
def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _job_status(job: Dict) -> str:
    s = job.get("status") or ""
    if s in ("completed", "submitted", "accepted"):
        return "success" if job.get("success") else "failed"
    return s


# ---------------------------------------------------------------------------
# Job → workflow dir
# ---------------------------------------------------------------------------
def write_job_workflow(job: Dict, actions: List[Dict], force: bool = False) -> Tuple[Path, bool]:
    """Write/update a job workflow dir. Returns (path, was_written)."""
    job_dir = JOBS_DIR / job["id"]
    marker  = job_dir / MARKER_FILE

    if job_dir.exists() and not force and marker.exists():
        return job_dir, False  # already synced, skip

    job_dir.mkdir(parents=True, exist_ok=True)
    marker.write_text("ironclaw-job\n", encoding="utf-8")

    status       = _job_status(job)
    started      = _iso(job.get("started_at"))
    completed    = _iso(job.get("completed_at"))
    exec_secs    = job.get("actual_time_secs") or 0

    metadata: Dict[str, Any] = {
        "task_id":    f"job-{job['id']}",
        "task_name":  job.get("title") or f"Job {job['id'][:8]}",
        "instruction": job.get("description") or "",
        "start_time": started,
        "end_time":   completed,
        "source":     job.get("source") or "ironclaw",
        "category":   job.get("category") or "",
        "conversation_id": job.get("conversation_id"),
        "repair_attempts": job.get("repair_attempts") or 0,
        "actual_cost": float(job.get("actual_cost") or 0),
        "job_mode": job.get("job_mode") or "",
        "total_tokens_used": job.get("total_tokens_used") or 0,
        "execution_outcome": {
            "status":         status,
            "execution_time": exec_secs,
            "iterations":     len(actions),
            "failure_reason": job.get("failure_reason") or "",
        },
        "_synced_by": "sync_ironclaw_workflows",
        "_synced_at": datetime.now(timezone.utc).isoformat(),
    }
    (job_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, default=str), encoding="utf-8"
    )

    # Write trajectory (traj.jsonl) from job_actions
    if actions:
        lines = []
        for act in actions:
            try:
                inp = json.loads(act.get("input_json") or "{}")
            except Exception:
                inp = {}
            try:
                out = json.loads(act.get("output_json") or "{}")
            except Exception:
                out = {}
            step = {
                "step":      act["sequence_num"],
                "backend":   "ironclaw",
                "tool":      act.get("tool_name") or "unknown",
                "input":     inp,
                "result": {
                    "status": "success" if act.get("success") else "error",
                    "output": out,
                    "error":  act.get("error_message") or "",
                },
                "timestamp":   _iso(act.get("created_at")),
                "duration_ms": act.get("duration_ms"),
                "cost":        float(act.get("cost") or 0),
            }
            lines.append(json.dumps(step, default=str))
        (job_dir / "traj.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    return job_dir, True


# ---------------------------------------------------------------------------
# Routine → workflow dir
# ---------------------------------------------------------------------------
def write_routine_workflow(routine: Dict, runs: List[Dict], force: bool = False) -> Tuple[Path, bool]:
    """Write/update a routine workflow dir. Returns (path, was_written)."""
    routine_dir = ROUTINES_DIR / routine["id"]
    marker      = routine_dir / MARKER_FILE

    # For routines, always overwrite — run_count/last_run_at change over time
    if routine_dir.exists() and not force and marker.exists():
        # Check if run_count changed (rough re-sync signal)
        meta_file = routine_dir / "metadata.json"
        if meta_file.exists():
            try:
                old = json.loads(meta_file.read_text(encoding="utf-8"))
                if old.get("run_count") == routine.get("run_count"):
                    return routine_dir, False
            except Exception:
                pass

    routine_dir.mkdir(parents=True, exist_ok=True)
    marker.write_text("ironclaw-routine\n", encoding="utf-8")

    try:
        trigger_config = json.loads(routine.get("trigger_config_json") or "{}")
    except Exception:
        trigger_config = {}
    try:
        action_config = json.loads(routine.get("action_config_json") or "{}")
    except Exception:
        action_config = {}

    last_run_status = "unknown"
    if runs:
        last_run_status = runs[0].get("status") or "unknown"

    # Map routine status to workflow status
    status_map = {"ok": "success", "failed": "failed", "attention": "attention",
                  "running": "running", "unknown": "unknown"}
    wf_status = status_map.get(last_run_status, last_run_status)

    action_prompt = action_config.get("prompt") or action_config.get("title") or ""

    metadata: Dict[str, Any] = {
        "task_id":    f"routine-{routine['id']}",
        "task_name":  routine.get("name") or f"Routine {routine['id'][:8]}",
        "instruction": routine.get("description") or action_prompt,
        "start_time": _iso(routine.get("last_run_at")),
        "end_time":   _iso(routine.get("last_run_at")),
        "trigger_type": routine.get("trigger_type") or "",
        "trigger_config": trigger_config,
        "action_type": routine.get("action_type") or "",
        "enabled":    routine.get("enabled"),
        "run_count":  routine.get("run_count") or 0,
        "consecutive_failures": routine.get("consecutive_failures") or 0,
        "next_fire_at": _iso(routine.get("next_fire_at")),
        "cooldown_secs": routine.get("cooldown_secs"),
        "execution_outcome": {
            "status":       wf_status,
            "execution_time": 0,
            "iterations":   routine.get("run_count") or 0,
        },
        "recent_runs": [
            {
                "id":            r.get("id"),
                "trigger_type":  r.get("trigger_type"),
                "trigger_detail": r.get("trigger_detail"),
                "started_at":    _iso(r.get("started_at")),
                "completed_at":  _iso(r.get("completed_at")),
                "status":        r.get("status"),
                "result_summary": r.get("result_summary"),
                "tokens_used":   r.get("tokens_used"),
                "job_id":        r.get("job_id"),
            }
            for r in runs[:10]
        ],
        "_synced_by": "sync_ironclaw_workflows",
        "_synced_at": datetime.now(timezone.utc).isoformat(),
    }
    (routine_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, default=str), encoding="utf-8"
    )

    # Write traj.jsonl from routine_runs (each run = one trajectory step)
    if runs:
        lines = []
        for i, r in enumerate(reversed(runs)):  # chronological order
            step = {
                "step":      i + 1,
                "backend":   "ironclaw",
                "tool":      f"routine.{routine.get('action_type') or 'run'}",
                "input":     {"trigger": r.get("trigger_detail") or r.get("trigger_type")},
                "result": {
                    "status": "success" if r.get("status") == "ok" else "error",
                    "output": {"summary": r.get("result_summary") or ""},
                    "error":  "" if r.get("status") == "ok" else (r.get("result_summary") or ""),
                },
                "timestamp":   _iso(r.get("started_at")),
                "duration_ms": None,
            }
            lines.append(json.dumps(step, default=str))
        (routine_dir / "traj.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    return routine_dir, True


# ---------------------------------------------------------------------------
# Remove synced dirs
# ---------------------------------------------------------------------------
def remove_synced() -> None:
    total = 0
    for root_dir in (JOBS_DIR, ROUTINES_DIR):
        if not root_dir.exists():
            continue
        import shutil
        for d in root_dir.iterdir():
            if d.is_dir() and (d / MARKER_FILE).exists():
                shutil.rmtree(str(d))
                print(f"  Removed {d}")
                total += 1
    print(f"Removed {total} synced workflow dir(s).")


# ---------------------------------------------------------------------------
# Main sync loop
# ---------------------------------------------------------------------------
def sync(db_url: str, force: bool = False, dry_run: bool = False) -> None:
    with _pg(db_url) as cur:
        jobs     = _fetch_jobs(cur)
        routines = _fetch_routines(cur)

    print(f"Found {len(jobs)} job(s), {len(routines)} routine(s)")

    job_written = job_skipped = 0
    for job in jobs:
        actions = []
        if not dry_run:
            with _pg(db_url) as cur:
                actions = _fetch_job_actions(cur, job["id"])
        status = _job_status(job)
        if dry_run:
            print(f"  [JOB]     {job.get('title')!r} ({status}) — {job['id'][:8]}")
            continue
        _, written = write_job_workflow(job, actions, force=force)
        if written:
            job_written += 1
            print(f"  [JOB] wrote  {job.get('title')!r} ({status})")
        else:
            job_skipped += 1

    routine_written = routine_skipped = 0
    for routine in routines:
        runs = []
        if not dry_run:
            with _pg(db_url) as cur:
                runs = _fetch_routine_runs(cur, routine["id"])
        if dry_run:
            enabled = "on" if routine.get("enabled") else "off"
            print(f"  [ROUTINE] {routine.get('name')!r} ({routine.get('trigger_type')}, {enabled}) — {routine['id'][:8]}")
            continue
        _, written = write_routine_workflow(routine, runs, force=force)
        if written:
            routine_written += 1
            print(f"  [ROUTINE] wrote  {routine.get('name')!r} (runs: {routine.get('run_count') or 0})")
        else:
            routine_skipped += 1

    if not dry_run:
        print(f"\nJobs:     {job_written} written, {job_skipped} unchanged")
        print(f"Routines: {routine_written} written, {routine_skipped} unchanged")
        print(f"Output:   {LOGS_ROOT}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    args = set(sys.argv[1:])
    dry_run  = "--dry-run"  in args
    force    = "--force"    in args
    watch    = "--watch"    in args
    remove   = "--remove"   in args

    db_url = _load_db_url()

    if remove:
        remove_synced()
        sys.exit(0)

    interval = 60
    if watch:
        # Parse optional --interval=N
        for a in sys.argv[1:]:
            m = re.match(r"--interval=(\d+)", a)
            if m:
                interval = int(m.group(1))

    while True:
        try:
            sync(db_url, force=force, dry_run=dry_run)
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
        if not watch:
            break
        print(f"\nWatching — next sync in {interval}s  (Ctrl-C to stop)\n")
        try:
            time.sleep(interval)
        except KeyboardInterrupt:
            break
