import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "enhancer.db"

def migrate_to_v2():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(tweak_history)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if "schema_version" not in columns:
        print("[MIGRATION] Adding 'schema_version' column...")
        cursor.execute("ALTER TABLE tweak_history ADD COLUMN schema_version TEXT")
        cursor.execute("UPDATE tweak_history SET schema_version = '1' WHERE schema_version IS NULL")
    
    if "verified_at" not in columns:
        print("[MIGRATION] Adding 'verified_at' column...")
        cursor.execute("ALTER TABLE tweak_history ADD COLUMN verified_at TIMESTAMP")
    
    conn.commit()
    conn.close()
    print("[MIGRATION] Database upgraded to v2 successfully.")