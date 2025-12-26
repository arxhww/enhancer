import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "enhancer.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tweak_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tweak_id TEXT NOT NULL,
            applied_at TIMESTAMP NOT NULL,
            reverted_at TIMESTAMP,
            status TEXT NOT NULL,
            error_message TEXT
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
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO tweak_history (tweak_id, applied_at, status)
        VALUES (?, ?, ?)
    """, (tweak_id, datetime.now(), "pending"))
    
    history_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return history_id


def save_snapshot(history_id, registry_path, key_name, old_value, old_type, value_existed, subkey_existed):
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    value_str = json.dumps(old_value) if old_value is not None else None
    
    cursor.execute("""
        INSERT INTO snapshots (history_id, registry_path, key_name, old_value, old_type, value_existed, subkey_existed)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (history_id, registry_path, key_name, value_str, old_type, value_existed, subkey_existed))
    
    conn.commit()
    conn.close()


def save_snapshot_v2(history_id: int, snapshot):
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO snapshots_v2 (history_id, action_type, metadata_json)
        VALUES (?, ?, ?)
    """, (history_id, snapshot.action_type, json.dumps(snapshot.metadata)))
    
    conn.commit()
    conn.close()


def mark_success(history_id: int):
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE tweak_history
        SET status = 'applied'
        WHERE id = ?
    """, (history_id,))
    
    conn.commit()
    conn.close()


def mark_rolled_back(history_id: int, error_message=None):
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    if error_message:
        cursor.execute("""
            UPDATE tweak_history
            SET status = 'rolled_back', error_message = ?
            WHERE id = ?
        """, (error_message, history_id))
    else:
        cursor.execute("""
            UPDATE tweak_history
            SET status = 'rolled_back'
            WHERE id = ?
        """, (history_id,))
    
    conn.commit()
    conn.close()


def mark_reverted(history_id: int):
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE tweak_history
        SET status = 'reverted', reverted_at = ?
        WHERE id = ?
    """, (datetime.now(), history_id))
    
    conn.commit()
    conn.close()


def get_snapshots(history_id: int) -> list:
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT registry_path, key_name, old_value, old_type, value_existed, subkey_existed
        FROM snapshots
        WHERE history_id = ?
        ORDER BY id ASC
    """, (history_id,))
    
    snapshots = []
    for row in cursor.fetchall():
        path, key, value_str, reg_type, value_existed, subkey_existed = row
        value = json.loads(value_str) if value_str else None
        snapshots.append({
            "path": path,
            "key": key,
            "value": value,
            "type": reg_type,
            "value_existed": bool(value_existed),
            "subkey_existed": bool(subkey_existed)
        })
    
    conn.close()
    return snapshots


def get_snapshots_v2(history_id: int) -> list:
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT action_type, metadata_json
        FROM snapshots_v2
        WHERE history_id = ?
        ORDER BY id ASC
    """, (history_id,))
    
    snapshots = []
    for row in cursor.fetchall():
        action_type, metadata_json = row
        metadata = json.loads(metadata_json)
        snapshots.append({
            "action_type": action_type,
            "metadata": metadata
        })
    
    conn.close()
    return snapshots


def get_active_tweaks() -> list:
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, tweak_id, applied_at
        FROM tweak_history
        WHERE status = 'applied'
        ORDER BY applied_at DESC
    """)
    
    tweaks = []
    for row in cursor.fetchall():
        tweaks.append({
            "id": row[0],
            "tweak_id": row[1],
            "applied_at": row[2]
        })
    
    conn.close()
    return tweaks


def mark_noop(history_id: int):
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE tweak_history
        SET status = 'noop'
        WHERE id = ?
    """, (history_id,))
    
    conn.commit()
    conn.close()


init_db()