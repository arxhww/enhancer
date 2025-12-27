import sqlite3
import pytest
from pathlib import Path
from datetime import timedelta

from core.recovery import RecoveryManager
from core.tweak_manager import TweakManager
from core.rollback import init_db, create_history_entry
from core.time import DEFAULT_TIME_PROVIDER as TIME


TEST_DB = Path(__file__).parent / "test_recovery.db"


@pytest.fixture(autouse=True)
def isolated_db():
    import core.rollback as roll_mod
    import core.recovery as rec_mod

    original_roll = roll_mod.DB_PATH
    original_rec = rec_mod.DB_PATH

    roll_mod.DB_PATH = TEST_DB
    rec_mod.DB_PATH = TEST_DB

    init_db()

    yield

    if TEST_DB.exists():
        TEST_DB.unlink()

    roll_mod.DB_PATH = original_roll
    rec_mod.DB_PATH = original_rec


def test_scan_detects_pending():
    hid = create_history_entry("test.pending@1.0")

    rm = RecoveryManager()
    issues = rm.scan_for_issues()

    assert len(issues) == 1
    assert issues[0]["type"] == "stuck_pending"
    assert issues[0]["history_id"] == hid


def test_scan_detects_stuck_applying():
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()

    old_time = TIME.now() - timedelta(minutes=10)
    cursor.execute(
        "INSERT INTO tweak_history (tweak_id, applied_at, status) VALUES (?, ?, ?)",
        ("test.applying@1.0", old_time, "applying"),
    )
    hid = cursor.lastrowid
    conn.commit()
    conn.close()

    rm = RecoveryManager()
    issues = rm.scan_for_issues()

    assert len(issues) == 1
    assert issues[0]["type"] == "stuck_applying"
    assert issues[0]["history_id"] == hid


def test_recover_pending_marks_recovered():
    hid = create_history_entry("test.recover.pending@1.0")

    manager = TweakManager()
    rm = RecoveryManager()

    result = rm.recover_all(manager)

    assert result["issues_found"] == 1
    assert result["recovered"] == 1

    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT status, error_message FROM tweak_history WHERE id = ?",
        (hid,),
    )
    status, msg = cursor.fetchone()
    conn.close()

    assert status == "recovered"
    assert "pending" in msg.lower()


def test_recovery_fails_hard_on_rollback_error():
    hid = create_history_entry("test.fail@1.0")

    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE tweak_history SET status = 'applying' WHERE id = ?",
        (hid,),
    )
    conn.commit()
    conn.close()

    manager = TweakManager()

    def failing_rollback(history_id):
        raise Exception("forced rollback failure")

    original = manager._rollback_execution
    manager._rollback_execution = failing_rollback

    rm = RecoveryManager()

    with pytest.raises(RuntimeError):
        rm.recover_all(manager)

    manager._rollback_execution = original