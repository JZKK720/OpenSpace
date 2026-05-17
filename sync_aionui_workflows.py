#!/usr/bin/env python3
"""Sync exported AionUi workflow directories into OpenSpace's workflow board.

OpenSpace already discovers workflows by scanning ``logs/recordings`` and
``logs/trajectories`` for directories that contain a ``metadata.json`` or
``traj.jsonl`` file. This script mirrors AionUi workflow data into
``logs/recordings/aionui-workflows/`` so the dashboard can show future
AgentOS / AionUi workflows without new backend routes.

Supported sources:
- OpenSpace-style workflow directories that already contain ``metadata.json``
    or ``traj.jsonl``.
- AionUi JSON conversation exports with the shape
    ``{"version": 1, "conversation": {...}, "messages": [...]}``.
- An AionUi data directory or ``aionui.db`` SQLite file with ``conversations``
    and ``messages`` tables.

Usage:
    python sync_aionui_workflows.py
    python sync_aionui_workflows.py --source path/to/aionui-exports
    python sync_aionui_workflows.py --dry-run
    python sync_aionui_workflows.py --force
    python sync_aionui_workflows.py --remove

Environment:
    AIONUI_WORKFLOWS_SOURCE_DIR   host path containing exported workflow dirs
                                  (default: logs/imports/aionui relative to repo root)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, List, Tuple

OPENSPACE_ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE_ROOT = OPENSPACE_ROOT / "logs" / "imports" / "aionui"
TARGET_ROOT = OPENSPACE_ROOT / "logs" / "recordings" / "aionui-workflows"
MARKER_FILE = ".aionui_sync"
AIONUI_DATABASE_NAME = "aionui.db"
AIONUI_EXPORT_ARTIFACT = "aionui_export.json"


def _load_env_value(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    if value:
        return value

    env_file = OPENSPACE_ROOT / ".env"
    if not env_file.exists():
        return None

    pattern = re.compile(rf"^\s*{re.escape(name)}\s*=\s*(.+?)\s*$")
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#"):
            continue
        match = pattern.match(line)
        if match:
            return match.group(1).strip().strip('"').strip("'")
    return None


def resolve_source_root(source: str | None = None) -> Path:
    raw = source or _load_env_value("AIONUI_WORKFLOWS_SOURCE_DIR") or str(DEFAULT_SOURCE_ROOT)
    path = Path(raw)
    if not path.is_absolute():
        path = OPENSPACE_ROOT / path
    return path


def _is_workflow_dir(path: Path) -> bool:
    return (path / "metadata.json").exists() or (path / "traj.jsonl").exists()


def _safe_json_loads(raw: Any) -> Any:
    if raw is None:
        return None
    if isinstance(raw, (dict, list)):
        return raw
    if not isinstance(raw, str):
        return raw

    text = raw.strip()
    if not text:
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return raw


def _stringify_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def _message_text(raw_content: Any) -> str:
    parsed = _safe_json_loads(raw_content)

    if isinstance(parsed, dict):
        content = parsed.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, dict):
            nested = content.get("content")
            if isinstance(nested, str):
                return nested
        return json.dumps(parsed, ensure_ascii=False)

    if isinstance(parsed, list):
        return json.dumps(parsed, ensure_ascii=False)
    if parsed is None:
        return ""
    return str(parsed)


def _timestamp_to_iso(value: Any) -> str | None:
    if value in (None, ""):
        return None

    try:
        return datetime.fromtimestamp(float(value) / 1000.0, tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def _compact_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _load_skills(extra: Any) -> List[str]:
    parsed = _safe_json_loads(extra)
    if not isinstance(parsed, dict):
        return []

    loaded = parsed.get("loadedSkills")
    if not isinstance(loaded, list):
        return []

    selected: List[str] = []
    for item in loaded:
        if isinstance(item, str) and item.strip():
            selected.append(item.strip())
            continue
        if isinstance(item, dict):
            for key in ("name", "id", "slug"):
                value = item.get(key)
                if isinstance(value, str) and value.strip():
                    selected.append(value.strip())
                    break

    deduped: List[str] = []
    for skill in selected:
        if skill not in deduped:
            deduped.append(skill)
    return deduped


def _parse_model_info(raw_model: Any) -> dict[str, Any]:
    parsed = _safe_json_loads(raw_model)
    if not isinstance(parsed, dict):
        if raw_model:
            return {"name": str(raw_model)}
        return {}

    return {
        "name": parsed.get("useModel") or parsed.get("name"),
        "platform": parsed.get("platform"),
    }


def _conversation_directory_name(conversation_id: str) -> str:
    safe_id = re.sub(r"[^A-Za-z0-9._-]+", "-", conversation_id or "").strip("-")
    return f"aionui-{safe_id or 'conversation'}"


def _conversation_source_updated_at(bundle: dict[str, Any]) -> Any:
    conversation = bundle.get("conversation") or {}
    return conversation.get("updated_at") or bundle.get("exportedAt") or bundle.get("source_mtime")


def _load_existing_metadata(destination: Path) -> dict[str, Any]:
    metadata_file = destination / "metadata.json"
    if not metadata_file.exists():
        return {}

    try:
        return json.loads(metadata_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _resolve_aionui_database(source_root: Path) -> Path | None:
    if source_root.is_file():
        return source_root if source_root.name.lower() == AIONUI_DATABASE_NAME else None

    for candidate in (
        source_root / AIONUI_DATABASE_NAME,
        source_root / "aionui" / AIONUI_DATABASE_NAME,
    ):
        if candidate.exists():
            return candidate
    return None


def _is_aionui_export_payload(payload: Any) -> bool:
    return (
        isinstance(payload, dict)
        and isinstance(payload.get("conversation"), dict)
        and isinstance(payload.get("messages"), list)
    )


def _load_export_bundle(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if not _is_aionui_export_payload(payload):
        return None

    conversation = dict(payload.get("conversation") or {})
    conversation_id = str(conversation.get("id") or path.stem)
    conversation["id"] = conversation_id

    return {
        "conversation": conversation,
        "messages": [dict(message) if isinstance(message, dict) else {"content": message} for message in payload.get("messages") or []],
        "exportedAt": payload.get("exportedAt"),
        "source_mtime": path.stat().st_mtime_ns,
        "sync_source": "export",
        "source_path": str(path),
    }


def _discover_aionui_export_files(root: Path, *, max_depth: int = 6) -> List[Path]:
    discovered: dict[str, Path] = {}

    def scan(path: Path, depth: int) -> None:
        if depth > max_depth or not path.exists():
            return

        if path.is_file():
            if path.suffix.lower() != ".json":
                return
            if _load_export_bundle(path):
                discovered.setdefault(str(path.resolve()), path)
            return

        try:
            children = list(path.iterdir())
        except OSError:
            return

        for child in children:
            try:
                is_directory = child.is_dir()
            except OSError:
                continue

            if is_directory:
                scan(child, depth + 1)
            elif child.suffix.lower() == ".json" and _load_export_bundle(child):
                discovered.setdefault(str(child.resolve()), child)

    scan(root, 0)
    return sorted(discovered.values(), key=lambda item: str(item).lower())


def _load_bundles_from_exports(source_root: Path) -> List[dict[str, Any]]:
    bundles: List[dict[str, Any]] = []
    for export_file in _discover_aionui_export_files(source_root):
        bundle = _load_export_bundle(export_file)
        if bundle:
            bundles.append(bundle)
    return bundles


def _open_database_readonly(db_path: Path) -> sqlite3.Connection:
    uri = f"{db_path.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _load_bundles_from_database(source_root: Path) -> List[dict[str, Any]]:
    db_path = _resolve_aionui_database(source_root)
    if not db_path or not db_path.exists():
        return []

    bundles: List[dict[str, Any]] = []
    with _open_database_readonly(db_path) as connection:
        conversations = [dict(row) for row in connection.execute("SELECT * FROM conversations ORDER BY created_at")]
        messages_by_conversation: dict[str, List[dict[str, Any]]] = {}
        for row in connection.execute("SELECT * FROM messages ORDER BY created_at"):
            message = dict(row)
            messages_by_conversation.setdefault(str(message.get("conversation_id") or ""), []).append(message)

        cron_jobs_by_conversation: dict[str, List[dict[str, Any]]] = {}
        for row in connection.execute("SELECT * FROM cron_jobs ORDER BY created_at"):
            cron_job = dict(row)
            cron_jobs_by_conversation.setdefault(str(cron_job.get("conversation_id") or ""), []).append(cron_job)

    for conversation in conversations:
        conversation_id = str(conversation.get("id") or "")
        bundles.append(
            {
                "conversation": conversation,
                "messages": messages_by_conversation.get(conversation_id, []),
                "cron_jobs": cron_jobs_by_conversation.get(conversation_id, []),
                "sync_source": "database",
                "source_path": str(db_path),
            }
        )

    return bundles


def _build_metadata(bundle: dict[str, Any]) -> dict[str, Any]:
    conversation = bundle.get("conversation") or {}
    messages = bundle.get("messages") or []
    cron_jobs = bundle.get("cron_jobs") or []
    extra = _safe_json_loads(conversation.get("extra"))
    model_info = _parse_model_info(conversation.get("model"))
    first_message_text = next((text for text in (_message_text(item.get("content")) for item in messages) if text), "")
    task_name = _compact_text(conversation.get("name") or conversation.get("id") or "AionUi conversation")
    loaded_skills = _load_skills(extra)

    start_time = _timestamp_to_iso(
        (messages[0].get("created_at") if messages else None) or conversation.get("created_at")
    )
    end_time = _timestamp_to_iso(
        (messages[-1].get("created_at") if messages else None)
        or conversation.get("updated_at")
        or conversation.get("created_at")
    )

    execution_time = 0.0
    if start_time and end_time:
        try:
            execution_time = round(
                (datetime.fromisoformat(end_time) - datetime.fromisoformat(start_time)).total_seconds(),
                2,
            )
        except ValueError:
            execution_time = 0.0

    if messages:
        status = conversation.get("status") or "completed"
    elif cron_jobs:
        status = "scheduled"
    else:
        status = conversation.get("status") or "unknown"

    metadata = {
        "task_id": conversation.get("id") or task_name,
        "task_name": task_name,
        "instruction": first_message_text or task_name,
        "start_time": start_time,
        "end_time": end_time,
        "execution_outcome": {
            "status": status,
            "iterations": len(messages),
            "execution_time": execution_time,
        },
        "aionui": {
            "conversation_id": conversation.get("id"),
            "conversation_type": conversation.get("type"),
            "conversation_source": conversation.get("source"),
            "conversation_status": conversation.get("status"),
            "message_count": len(messages),
            "hidden_message_count": sum(1 for item in messages if item.get("hidden")),
            "source_updated_at": _conversation_source_updated_at(bundle),
            "sync_source": bundle.get("sync_source"),
            "sync_source_path": bundle.get("source_path"),
            "model_name": model_info.get("name"),
            "model_platform": model_info.get("platform"),
        },
    }

    if isinstance(extra, dict):
        cron_job_id = extra.get("cronJobId")
        session_mode = extra.get("sessionMode")
        if cron_job_id:
            metadata["aionui"]["cron_job_id"] = cron_job_id
        if session_mode:
            metadata["aionui"]["session_mode"] = session_mode

    if loaded_skills:
        metadata["skill_selection"] = {"selected": loaded_skills}

    if cron_jobs:
        metadata["aionui"]["cron_jobs"] = cron_jobs

    return metadata


def _build_trajectory(bundle: dict[str, Any]) -> List[dict[str, Any]]:
    conversation = bundle.get("conversation") or {}
    backend = conversation.get("type") or "aionui"
    trajectory: List[dict[str, Any]] = []

    for index, message in enumerate(bundle.get("messages") or [], start=1):
        trajectory.append(
            {
                "step": index,
                "timestamp": _timestamp_to_iso(message.get("created_at")) or "",
                "backend": backend,
                "tool": message.get("type") or "message",
                "result": {"status": message.get("status") or "success"},
                "conversation_id": conversation.get("id"),
                "message_id": message.get("id") or message.get("msg_id"),
                "position": message.get("position"),
                "hidden": bool(message.get("hidden")),
                "content": _message_text(message.get("content")),
            }
        )

    return trajectory


def _write_aionui_bundle(destination: Path, bundle: dict[str, Any]) -> None:
    metadata = _build_metadata(bundle)
    trajectory = _build_trajectory(bundle)
    export_payload = {
        "version": 1,
        "exportedAt": datetime.now(tz=timezone.utc).isoformat(),
        "conversation": bundle.get("conversation") or {},
        "messages": bundle.get("messages") or [],
    }

    destination.mkdir(parents=True, exist_ok=True)
    (destination / "metadata.json").write_text(_stringify_json(metadata), encoding="utf-8")
    (destination / AIONUI_EXPORT_ARTIFACT).write_text(_stringify_json(export_payload), encoding="utf-8")

    if bundle.get("cron_jobs"):
        (destination / "aionui_cron_jobs.json").write_text(
            _stringify_json(bundle.get("cron_jobs") or []),
            encoding="utf-8",
        )

    traj_file = destination / "traj.jsonl"
    if trajectory:
        with traj_file.open("w", encoding="utf-8") as handle:
            for step in trajectory:
                handle.write(json.dumps(step, ensure_ascii=False) + "\n")
    elif traj_file.exists():
        traj_file.unlink()

    (destination / MARKER_FILE).write_text("aionui-workflow\n", encoding="utf-8")


def discover_workflow_dirs(root: Path, *, max_depth: int = 6) -> List[Path]:
    discovered: dict[str, Path] = {}

    def scan(directory: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            children = list(directory.iterdir())
        except OSError:
            return

        for child in children:
            try:
                is_directory = child.is_dir()
            except OSError:
                continue

            if not is_directory:
                continue
            if _is_workflow_dir(child):
                discovered.setdefault(str(child.resolve()), child)
                continue
            scan(child, depth + 1)

    if root.exists():
        scan(root, 0)

    return sorted(discovered.values(), key=lambda item: str(item).lower())


def _sync_workflow_directories(
    source_root: Path,
    target_root: Path,
    workflow_dirs: Iterable[Path],
    *,
    force: bool = False,
    dry_run: bool = False,
) -> Tuple[int, int]:
    synced = 0
    skipped = 0

    for workflow_dir in workflow_dirs:
        relative_path = workflow_dir.relative_to(source_root)
        destination = target_root / relative_path
        marker = destination / MARKER_FILE

        if destination.exists():
            if force and marker.exists():
                if not dry_run:
                    shutil.rmtree(destination)
            else:
                skipped += 1
                continue

        synced += 1
        if dry_run:
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(workflow_dir, destination)
        marker.write_text("aionui-workflow\n", encoding="utf-8")

    return synced, skipped


def _sync_aionui_bundles(
    bundles: Iterable[dict[str, Any]],
    target_root: Path,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> Tuple[int, int]:
    synced = 0
    skipped = 0

    for bundle in bundles:
        conversation = bundle.get("conversation") or {}
        conversation_id = str(conversation.get("id") or "")
        destination = target_root / _conversation_directory_name(conversation_id)
        marker = destination / MARKER_FILE

        if destination.exists():
            if not marker.exists():
                skipped += 1
                continue

            existing_metadata = _load_existing_metadata(destination)
            existing_aionui = existing_metadata.get("aionui") or {}
            same_source = str(existing_aionui.get("source_updated_at")) == str(_conversation_source_updated_at(bundle))
            same_count = existing_aionui.get("message_count") == len(bundle.get("messages") or [])
            if not force and same_source and same_count:
                skipped += 1
                continue

            if not dry_run:
                shutil.rmtree(destination)

        synced += 1
        if dry_run:
            continue

        _write_aionui_bundle(destination, bundle)

    return synced, skipped


def sync_workflows(source_root: Path, target_root: Path = TARGET_ROOT, *, force: bool = False, dry_run: bool = False) -> Tuple[int, int]:
    workflow_dirs = discover_workflow_dirs(source_root)
    if workflow_dirs:
        return _sync_workflow_directories(source_root, target_root, workflow_dirs, force=force, dry_run=dry_run)

    db_bundles = _load_bundles_from_database(source_root)
    if db_bundles:
        return _sync_aionui_bundles(db_bundles, target_root, force=force, dry_run=dry_run)

    export_bundles = _load_bundles_from_exports(source_root)
    if export_bundles:
        return _sync_aionui_bundles(export_bundles, target_root, force=force, dry_run=dry_run)

    return 0, 0


def remove_synced_workflows(target_root: Path = TARGET_ROOT) -> int:
    removed = 0
    for workflow_dir in reversed(discover_workflow_dirs(target_root)):
        marker = workflow_dir / MARKER_FILE
        if not marker.exists():
            continue
        shutil.rmtree(workflow_dir)
        removed += 1

    if not target_root.exists():
        return removed

    for directory in sorted((path for path in target_root.rglob("*") if path.is_dir()), reverse=True):
        try:
            next(directory.iterdir())
        except StopIteration:
            directory.rmdir()
        except OSError:
            continue

    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description="Mirror AionUi workflow directories, exports, or live conversation data into OpenSpace recordings.")
    parser.add_argument("--source", help="Host directory, export file, data directory, or aionui.db path")
    parser.add_argument("--target", help="Target directory under OpenSpace recordings")
    parser.add_argument("--dry-run", action="store_true", help="Preview what would be synced without copying")
    parser.add_argument("--force", action="store_true", help="Overwrite previously synced workflow directories")
    parser.add_argument("--remove", action="store_true", help="Delete workflow directories created by this sync script")
    args = parser.parse_args()

    target_root = Path(args.target) if args.target else TARGET_ROOT
    if not target_root.is_absolute():
        target_root = OPENSPACE_ROOT / target_root

    if args.remove:
        removed = remove_synced_workflows(target_root)
        print(f"Removed {removed} synced AionUi workflow dir(s).")
        return 0

    source_root = resolve_source_root(args.source)
    if not source_root.exists():
        print(f"No AionUi workflow source found at {source_root}")
        return 0

    synced, skipped = sync_workflows(source_root, target_root, force=args.force, dry_run=args.dry_run)
    action = "Would sync" if args.dry_run else "Synced"
    print(f"{action} {synced} AionUi workflow item(s); skipped {skipped} existing item(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())