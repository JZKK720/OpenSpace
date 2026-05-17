import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sync_aionui_workflows import MARKER_FILE, remove_synced_workflows, sync_workflows


def _create_aionui_database(db_path: Path) -> None:
    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
        CREATE TABLE conversations (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            extra TEXT NOT NULL,
            model TEXT,
            status TEXT,
            source TEXT,
            channel_chat_id TEXT,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );
        CREATE TABLE messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            msg_id TEXT,
            type TEXT NOT NULL,
            content TEXT NOT NULL,
            position TEXT,
            status TEXT,
            created_at INTEGER NOT NULL,
            hidden INTEGER DEFAULT 0
        );
        CREATE TABLE cron_jobs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            schedule_kind TEXT NOT NULL,
            schedule_value TEXT NOT NULL,
            schedule_tz TEXT,
            schedule_description TEXT NOT NULL,
            payload_message TEXT NOT NULL,
            conversation_id TEXT NOT NULL,
            conversation_title TEXT,
            agent_type TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_at INTEGER,
            updated_at INTEGER,
            next_run_at INTEGER,
            last_run_at INTEGER,
            last_status TEXT,
            last_error TEXT,
            run_count INTEGER DEFAULT 0,
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3,
            execution_mode TEXT DEFAULT 'existing',
            agent_config TEXT,
            description TEXT
        );
        """
    )
    connection.execute(
        """
        INSERT INTO conversations (id, user_id, name, type, extra, model, status, source, channel_chat_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "conv-001",
            "user-1",
            "Morning sync",
            "aionrs",
            json.dumps({"loadedSkills": ["planner", "reviewer"], "sessionMode": "chat"}),
            json.dumps({"platform": "custom", "name": "ollama-nemotron", "useModel": "nemotron3:33b-q8"}),
            None,
            "aionui",
            None,
            1_700_000_000_000,
            1_700_000_120_000,
        ),
    )
    connection.executemany(
        """
        INSERT INTO messages (id, conversation_id, msg_id, type, content, position, status, created_at, hidden)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                "msg-1",
                "conv-001",
                None,
                "text",
                json.dumps({"content": "Morning sync"}),
                "right",
                None,
                1_700_000_000_000,
                0,
            ),
            (
                "msg-2",
                "conv-001",
                None,
                "text",
                json.dumps({"content": "Ready"}),
                "left",
                None,
                1_700_000_120_000,
                0,
            ),
        ],
    )
    connection.execute(
        """
        INSERT INTO cron_jobs (id, name, enabled, schedule_kind, schedule_value, schedule_tz, schedule_description, payload_message, conversation_id, conversation_title, agent_type, created_by, created_at, updated_at, next_run_at, last_run_at, last_status, last_error, run_count, retry_count, max_retries, execution_mode, agent_config, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "cron-1",
            "Daily sync",
            1,
            "cron",
            "0 9 * * *",
            "UTC",
            "Every day at 09:00 UTC",
            "Morning sync",
            "conv-001",
            "Morning sync",
            "aionrs",
            "user-1",
            1_700_000_000_000,
            1_700_000_120_000,
            1_700_000_360_000,
            None,
            None,
            None,
            0,
            0,
            3,
            "existing",
            None,
            "Daily catch-up",
        ),
    )
    connection.commit()
    connection.close()


def test_sync_aionui_workflows_copies_exported_workflow_dirs(tmp_path):
    source_root = tmp_path / "exports"
    workflow_root = source_root / "runs" / "job-001"
    workflow_root.mkdir(parents=True)
    (workflow_root / "metadata.json").write_text("{}", encoding="utf-8")

    target_root = tmp_path / "recordings"
    synced, skipped = sync_workflows(source_root, target_root)

    synced_dir = target_root / "runs" / "job-001"
    assert synced == 1
    assert skipped == 0
    assert (synced_dir / "metadata.json").exists()
    assert (synced_dir / MARKER_FILE).exists()


def test_sync_aionui_workflows_preserves_unmanaged_dirs(tmp_path):
    source_root = tmp_path / "exports"
    workflow_root = source_root / "runs" / "job-001"
    workflow_root.mkdir(parents=True)
    (workflow_root / "metadata.json").write_text("{}", encoding="utf-8")

    target_root = tmp_path / "recordings"
    existing_dir = target_root / "runs" / "job-001"
    existing_dir.mkdir(parents=True)
    (existing_dir / "metadata.json").write_text('{"existing": true}', encoding="utf-8")

    synced, skipped = sync_workflows(source_root, target_root)

    assert synced == 0
    assert skipped == 1
    assert (existing_dir / "metadata.json").read_text(encoding="utf-8") == '{"existing": true}'


def test_sync_aionui_workflows_materializes_live_database_conversations(tmp_path):
    source_root = tmp_path / "aionui-data"
    source_root.mkdir()
    _create_aionui_database(source_root / "aionui.db")

    target_root = tmp_path / "recordings"
    synced, skipped = sync_workflows(source_root, target_root)

    synced_dir = target_root / "aionui-conv-001"
    metadata = json.loads((synced_dir / "metadata.json").read_text(encoding="utf-8"))
    traj_lines = (synced_dir / "traj.jsonl").read_text(encoding="utf-8").strip().splitlines()
    export_payload = json.loads((synced_dir / "aionui_export.json").read_text(encoding="utf-8"))
    cron_jobs = json.loads((synced_dir / "aionui_cron_jobs.json").read_text(encoding="utf-8"))

    assert synced == 1
    assert skipped == 0
    assert (synced_dir / MARKER_FILE).exists()
    assert metadata["task_name"] == "Morning sync"
    assert metadata["instruction"] == "Morning sync"
    assert metadata["execution_outcome"]["status"] == "completed"
    assert metadata["aionui"]["sync_source"] == "database"
    assert metadata["aionui"]["message_count"] == 2
    assert metadata["skill_selection"]["selected"] == ["planner", "reviewer"]
    assert len(traj_lines) == 2
    assert export_payload["conversation"]["id"] == "conv-001"
    assert len(export_payload["messages"]) == 2
    assert cron_jobs[0]["id"] == "cron-1"


def test_sync_aionui_workflows_refreshes_managed_database_conversations(tmp_path):
    source_root = tmp_path / "aionui-data"
    source_root.mkdir()
    db_path = source_root / "aionui.db"
    _create_aionui_database(db_path)

    target_root = tmp_path / "recordings"
    first_synced, first_skipped = sync_workflows(source_root, target_root)
    assert first_synced == 1
    assert first_skipped == 0

    connection = sqlite3.connect(db_path)
    connection.execute(
        "UPDATE conversations SET updated_at = ? WHERE id = ?",
        (1_700_000_180_000, "conv-001"),
    )
    connection.execute(
        """
        INSERT INTO messages (id, conversation_id, msg_id, type, content, position, status, created_at, hidden)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "msg-3",
            "conv-001",
            None,
            "text",
            json.dumps({"content": "Updated"}),
            "left",
            None,
            1_700_000_180_000,
            0,
        ),
    )
    connection.commit()
    connection.close()

    synced, skipped = sync_workflows(source_root, target_root)
    synced_dir = target_root / "aionui-conv-001"
    metadata = json.loads((synced_dir / "metadata.json").read_text(encoding="utf-8"))
    traj_lines = (synced_dir / "traj.jsonl").read_text(encoding="utf-8").strip().splitlines()

    assert synced == 1
    assert skipped == 0
    assert metadata["aionui"]["message_count"] == 3
    assert len(traj_lines) == 3


def test_remove_synced_workflows_removes_marked_dirs_only(tmp_path):
    target_root = tmp_path / "recordings"

    managed_dir = target_root / "managed"
    managed_dir.mkdir(parents=True)
    (managed_dir / "metadata.json").write_text("{}", encoding="utf-8")
    (managed_dir / MARKER_FILE).write_text("aionui-workflow\n", encoding="utf-8")

    unmanaged_dir = target_root / "unmanaged"
    unmanaged_dir.mkdir(parents=True)
    (unmanaged_dir / "metadata.json").write_text("{}", encoding="utf-8")

    removed = remove_synced_workflows(target_root)

    assert removed == 1
    assert not managed_dir.exists()
    assert unmanaged_dir.exists()