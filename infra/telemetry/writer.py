import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parents[2] / "telemetry.db"

print(f"[TELEMETRY] writing to {DB_PATH}")

def init():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            tweak_id TEXT,
            history_id INTEGER,
            event TEXT NOT NULL,
            result TEXT,
            error TEXT
        )
    """)
    conn.commit()
    conn.close()

def emit(event: dict):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO events (ts, tweak_id, history_id, event, result, error)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.utcnow().isoformat(),
            event.get("tweak_id"),
            event.get("history_id"),
            event["event"],
            event.get("result"),
            str(event.get("error")) if event.get("error") else None,
        )
    )
    conn.commit()
    conn.close()

init()
