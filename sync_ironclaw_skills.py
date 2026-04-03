#!/usr/bin/env python3
"""Sync ironclaw SKILL.md files into OpenSpace's SkillStore (openspace.db).

Skills are copied to .openspace/ironclaw_skills/ so they are accessible
inside OpenSpace containers via the mounted .openspace volume, and rows
are upserted into skill_records + skill_tags so the dashboard shows them.

Usage:
    python sync_ironclaw_skills.py            # sync all skills
    python sync_ironclaw_skills.py --dry-run  # preview only, no writes
    python sync_ironclaw_skills.py --remove   # remove synced skills from DB
"""
from __future__ import annotations

import json
import re
import shutil
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent  # OpenSpace/
IRONCLAW_SKILLS_DIR = REPO_ROOT.parent / "ironclaw" / "skills"
OPENSPACE_DB = REPO_ROOT / ".openspace" / "openspace.db"
# Skills are copied here so they are accessible inside the container at
#   /app/.openspace/ironclaw_skills/<name>/SKILL.md
DEST_SKILLS_DIR = REPO_ROOT / ".openspace" / "ironclaw_skills"
# Container-side path prefix (as seen by dashboard/runtime containers)
CONTAINER_SKILLS_PREFIX = "/app/.openspace/ironclaw_skills"

SKILL_FILENAME = "SKILL.md"
SKILL_ID_FILENAME = ".skill_id"
CREATOR_ID = "ironclaw"

# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------
_FM_BLOCK = re.compile(r"^\s*---\r?\n(.*?)\r?\n---", re.DOTALL)
_LIST_ITEM = re.compile(r"^\s*-\s+(.+)$")


def _parse_yaml_frontmatter(content: str) -> Tuple[Dict[str, Any], List[str]]:
    """Parse SKILL.md frontmatter; return (flat_fields, tags).

    Handles both flat scalars and nested 'activation.tags' list.
    """
    m = _FM_BLOCK.match(content)
    if not m:
        return {}, []

    fm: Dict[str, Any] = {}
    tags: List[str] = []
    lines = m.group(1).split("\n")

    in_activation = False
    in_tags = False

    for line in lines:
        stripped = line.strip()

        # Detect top-level 'activation:' block
        if re.match(r"^activation\s*:", line):
            in_activation = True
            in_tags = False
            continue

        if in_activation:
            # Nested 'tags:' under activation
            if re.match(r"^\s+tags\s*:", line):
                in_tags = True
                continue
            # List items under activation.tags
            if in_tags:
                li = _LIST_ITEM.match(line)
                if li:
                    tags.append(li.group(1).strip())
                    continue
                # Either a new nested key or end of list
                if re.match(r"^\s+\w", line) and ":" in line:
                    in_tags = False
                    continue
            # Any non-indented line ends the activation block
            if not line.startswith(" ") and not line.startswith("\t"):
                in_activation = False
                in_tags = False

        # Flat key: value
        if not in_activation and ":" in line and not line.startswith(" "):
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            # Strip surrounding quotes
            if len(value) >= 2 and value[0] in ('"', "'") and value[-1] == value[0]:
                value = value[1:-1]
            if key:
                fm[key] = value

    return fm, tags


# ---------------------------------------------------------------------------
# Skill ID sidecar helpers
# ---------------------------------------------------------------------------
def _read_or_create_skill_id(name: str, skill_dir: Path) -> str:
    id_file = skill_dir / SKILL_ID_FILENAME
    if id_file.exists():
        existing = id_file.read_text(encoding="utf-8").strip()
        if existing:
            return existing
    new_id = f"{name}__imp_{uuid.uuid4().hex[:8]}"
    id_file.write_text(new_id + "\n", encoding="utf-8")
    return new_id


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def _connect() -> sqlite3.Connection:
    # Do NOT change journal_mode — the containers manage WAL mode.
    # After writing, call PRAGMA wal_checkpoint(TRUNCATE) and close cleanly
    # so the container's read-only connections are not blocked.
    conn = sqlite3.connect(str(OPENSPACE_DB), timeout=10)
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _upsert_skill(
    conn: sqlite3.Connection,
    skill_id: str,
    name: str,
    description: str,
    path: str,
    tags: List[str],
    now: str,
) -> None:
    conn.execute(
        """
        INSERT INTO skill_records (
            skill_id, name, description, path, is_active, category,
            visibility, creator_id,
            lineage_origin, lineage_generation,
            lineage_source_task_id, lineage_change_summary,
            lineage_content_diff, lineage_content_snapshot,
            lineage_created_at, lineage_created_by,
            total_selections, total_applied, total_completions, total_fallbacks,
            first_seen, last_updated
        ) VALUES (?,?,?,?,1,'workflow', 'private',?,
                  'imported',0,
                  NULL,'Imported from ironclaw',
                  '','{}',
                  ?,?,
                  0,0,0,0,
                  ?,?)
        ON CONFLICT(skill_id) DO UPDATE SET
            name=excluded.name,
            description=excluded.description,
            path=excluded.path,
            is_active=1,
            lineage_change_summary=excluded.lineage_change_summary,
            creator_id=excluded.creator_id,
            last_updated=excluded.last_updated
        """,
        (skill_id, name, description, path, CREATOR_ID, now, CREATOR_ID, now, now),
    )

    # Sync tags: delete old, insert new
    conn.execute("DELETE FROM skill_tags WHERE skill_id=?", (skill_id,))
    for tag in tags:
        if tag:
            conn.execute(
                "INSERT OR IGNORE INTO skill_tags (skill_id, tag) VALUES (?,?)",
                (skill_id, tag),
            )


def _remove_skill(conn: sqlite3.Connection, skill_id: str) -> None:
    conn.execute("DELETE FROM skill_records WHERE skill_id=?", (skill_id,))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def collect_skills() -> List[Path]:
    if not IRONCLAW_SKILLS_DIR.exists():
        print(f"ERROR: ironclaw skills dir not found: {IRONCLAW_SKILLS_DIR}", file=sys.stderr)
        sys.exit(1)
    return sorted(
        sd for sd in IRONCLAW_SKILLS_DIR.iterdir()
        if sd.is_dir() and (sd / SKILL_FILENAME).exists()
    )


def sync(dry_run: bool = False) -> None:
    skill_dirs = collect_skills()
    print(f"Found {len(skill_dirs)} ironclaw skill(s) to sync\n")

    if not OPENSPACE_DB.exists():
        print(f"ERROR: OpenSpace DB not found: {OPENSPACE_DB}", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc).isoformat()

    rows: List[tuple] = []  # (skill_id, name, description, container_path, src_sd, dest_dir, dest_md, tags)

    for sd in skill_dirs:
        content = (sd / SKILL_FILENAME).read_text(encoding="utf-8")
        fm, tags = _parse_yaml_frontmatter(content)

        name = fm.get("name") or sd.name
        description = fm.get("description") or ""
        dest_dir = DEST_SKILLS_DIR / name
        dest_md = dest_dir / SKILL_FILENAME
        # Container path: used as the 'path' field so dashboard can load source
        container_path = f"{CONTAINER_SKILLS_PREFIX}/{name}/{SKILL_FILENAME}"

        # Read/create skill_id from source dir (persists across syncs)
        if dry_run:
            skill_id = f"{name}__imp_preview"
        else:
            skill_id = _read_or_create_skill_id(name, sd)

        rows.append((skill_id, name, description, container_path, sd, dest_dir, dest_md, tags))

        status = "[DRY RUN] " if dry_run else ""
        tag_str = ", ".join(tags) if tags else "(none)"
        print(f"  {status}\u00bb {name}")
        print(f"       id:   {skill_id}")
        print(f"       desc: {description[:80]}")
        print(f"       tags: {tag_str}")
        print(f"       dest: {dest_md}")
        print()

    if dry_run:
        print("Dry run complete — no files or DB changes made.")
        return

    # Copy SKILL.md files to .openspace/ironclaw_skills/
    DEST_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    for skill_id, name, description, container_path, src_sd, dest_dir, dest_md, tags in rows:
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src_sd / SKILL_FILENAME), str(dest_md))
        # Write skill_id sidecar alongside the copy too
        (dest_dir / SKILL_ID_FILENAME).write_text(skill_id + "\n", encoding="utf-8")

    # Upsert into OpenSpace DB
    conn = _connect()
    try:
        conn.execute("BEGIN")
        for skill_id, name, description, container_path, src_sd, dest_dir, dest_md, tags in rows:
            _upsert_skill(conn, skill_id, name, description, container_path, tags, now)
        conn.commit()
        # Checkpoint WAL so the container's read-only connections see the changes
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        print(f"Synced {len(rows)} skill(s) into {OPENSPACE_DB}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def remove(dry_run: bool = False) -> None:
    """Remove all ironclaw-imported skills from the OpenSpace DB."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT skill_id, name FROM skill_records WHERE creator_id=?",
            (CREATOR_ID,),
        ).fetchall()
        if not rows:
            print("No ironclaw skills found in DB.")
            return
        print(f"{'[DRY RUN] ' if dry_run else ''}Removing {len(rows)} skill(s):")
        for skill_id, name in rows:
            print(f"  - {name} ({skill_id})")
        if not dry_run:
            conn.execute("BEGIN")
            conn.execute("DELETE FROM skill_records WHERE creator_id=?", (CREATOR_ID,))
            conn.commit()
            # Also remove copied files
            if DEST_SKILLS_DIR.exists():
                shutil.rmtree(str(DEST_SKILLS_DIR))
                print(f"Removed {DEST_SKILLS_DIR}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    args = set(sys.argv[1:])
    dry_run = "--dry-run" in args

    if "--remove" in args:
        remove(dry_run=dry_run)
    else:
        sync(dry_run=dry_run)
