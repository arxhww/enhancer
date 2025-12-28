import sqlite3
import json
from pathlib import Path
from datetime import datetime

from .time import DEFAULT_TIME_PROVIDER as TIME

DB_PATH = Path(__file__).parent.parent / "enhancer.db"


def init_db():
    sqlite3.register_adapter(datetime, lambda dt: dt.isoformat())
    sqlite3.register_converter(
        "TIMESTAMP", lambda s: datetime.fromisoformat(s.decode())
    )

    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.execute("PRAGMA journal_mode=WAL")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tweak_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tweak_id TEXT NOT NULL,
            applied_at TIMESTAMP NOT NULL,
            reverted_at TIMESTAMP,
            verified_at TIMESTAMP,
            status TEXT NOT NULL,
            error_message TEXT,
            schema_version INTEGER NOT NULL DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            history_id INTEGER NOT NULL,
            registry_path TEXT NOT NULL,
            key_name TEXT NOT NULL,
            old_value TEXT,
            old_type INTEGER,
            value_existed BOOLEAN NOT NULL,
            subkey_existed BOOLEAN NOT NULL,
            FOREIGN KEY (history_id) REFERENCES tweak_history(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS snapshots_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            history_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            FOREIGN KEY (history_id) REFERENCES tweak_history(id)
        )
    """)

    conn.commit()
    conn.close()


def create_history_entry(tweak_id: str) -> int:
    conn = sqlite3.connect(DB_PATH, timeout=10.0, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO tweak_history (tweak_id, applied_at, status)
        VALUES (?, ?, ?)
    """, (tweak_id, TIME.now(), "defined")) 

    history_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return history_id

def save_snapshot_v2(history_id: int, snapshot):
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO snapshots_v2 (history_id, action_type, metadata_json)
        VALUES (?, ?, ?)
    """, (history_id, snapshot.action_type, json.dumps(snapshot.metadata)))

    conn.commit()
    conn.close()
    
def get_snapshots_v2(history_id: int) -> list:
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT action_type, metadata_json
        FROM snapshots_v2
        WHERE history_id = ?
        ORDER BY id ASC
    """, (history_id,))

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "action_type": action_type,
            "metadata": json.loads(metadata_json)
        }
        for action_type, metadata_json in rows
    ]

def get_active_tweaks() -> list:
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, tweak_id, applied_at, status
        FROM tweak_history
        WHERE status = 'applied'
        ORDER BY applied_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "tweak_id": r[1],
            "applied_at": r[2],
            "status": r[3],
        }
        for r in rows
    ]
    
def clear_snapshots(history_id: int):
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM snapshots_v2
        WHERE history_id = ?
    """, (history_id,))

    conn.commit()
    conn.close()
    
def is_reverted(history_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT status FROM tweak_history WHERE id = ?",
        (history_id,)
    )
    row = cursor.fetchone()
    conn.close()

    return row is not None and row[0] == "reverted"

def get_latest_history_by_tweak_id(tweak_id: str):
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, status
        FROM tweak_history
        WHERE tweak_id = ?
        ORDER BY applied_at DESC
        LIMIT 1
        """,
        (tweak_id,)
    )

    row = cursor.fetchone()
    conn.close()
    return row

def mark_applied(history_id: int):
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE tweak_history
        SET status = 'applied'
        WHERE id = ?
    """, (history_id,))

    conn.commit()
    conn.close()

def get_history_by_tweak_id(tweak_id: str):
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, tweak_id, status, applied_at, reverted_at, verified_at
        FROM tweak_history
        WHERE tweak_id = ?
        ORDER BY applied_at ASC
        LIMIT 1
        """,
        (tweak_id,)
    )

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "tweak_id": row[1],
        "status": row[2],
        "applied_at": row[3],
        "reverted_at": row[4],
        "verified_at": row[5],
    }


init_db()