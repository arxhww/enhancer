import pytest
import sqlite3
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.tweak_state import TweakState, can_transition, TRANSITIONS
from core.state_machine import TweakStateMachine

TEST_DB_PATH = Path(__file__).parent / "test_enhancer.db"

@pytest.fixture(autouse=True)
def setup_test_db():
    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tweak_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL,
            error_message TEXT,
            verified_at TIMESTAMP
        )
    """)
    conn.commit()
    
    import core.state_machine as sm_module
    original_path = sm_module.DB_PATH
    sm_module.DB_PATH = TEST_DB_PATH
    
    yield
    
    conn.close()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    sm_module.DB_PATH = original_path


class TestTweakStateEnum:
    
    def test_valid_transitions(self):
        assert can_transition(TweakState.DEFINED, "validate")
        assert can_transition(TweakState.VALIDATED, "apply")
        assert can_transition(TweakState.APPLYING, "success")
    
    def test_invalid_transitions(self):
        assert not can_transition(TweakState.DEFINED, "apply")
        assert not can_transition(TweakState.VALIDATED, "verify")
        assert not can_transition(TweakState.VALIDATED, "revert")

    def test_failed_allows_revert(self):
        assert can_transition(TweakState.FAILED, "revert")


class TestStateMachineExecution:
    
    def test_simple_flow_success(self, setup_test_db):
        conn = sqlite3.connect(TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tweak_history (status) VALUES ('defined')")
        history_id = cursor.lastrowid
        conn.commit()
        conn.close()

        sm = TweakStateMachine(history_id, "defined")
        
        sm.transition("validate")
        assert sm.current_state == TweakState.VALIDATED
        
        sm.transition("apply")
        assert sm.current_state == TweakState.APPLYING
        
        sm.transition("success")
        assert sm.current_state == TweakState.APPLIED
        
        sm.transition("verify")
        assert sm.current_state == TweakState.VERIFIED
        
        conn = sqlite3.connect(TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT status, verified_at FROM tweak_history WHERE id=?", (history_id,))
        status, verified_at = cursor.fetchone()
        conn.close()
        
        assert status == "verified"
        assert verified_at is not None

    def test_flow_with_error_context(self, setup_test_db):
        conn = sqlite3.connect(TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tweak_history (status) VALUES ('applying')")
        history_id = cursor.lastrowid
        conn.commit()
        conn.close()

        sm = TweakStateMachine(history_id, "applying")
        error_msg = "Disk write failed"
        
        sm.transition("fail", context={"error_message": error_msg})
        
        assert sm.current_state == TweakState.FAILED
        
        conn = sqlite3.connect(TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT error_message FROM tweak_history WHERE id=?", (history_id,))
        db_error = cursor.fetchone()[0]
        conn.close()
        
        assert db_error == error_msg

    def test_verified_sets_timestamp_without_context(self, setup_test_db):
        conn = sqlite3.connect(TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tweak_history (status) VALUES ('applied')")
        history_id = cursor.lastrowid
        conn.commit()
        conn.close()

        sm = TweakStateMachine(history_id, "applied")
        
        sm.transition("verify")
        
        assert sm.current_state == TweakState.VERIFIED
        
        conn = sqlite3.connect(TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT verified_at FROM tweak_history WHERE id=?", (history_id,))
        verified_at = cursor.fetchone()[0]
        conn.close()
        
        assert verified_at is not None

    def test_invalid_transition_raises(self, setup_test_db):
        conn = sqlite3.connect(TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tweak_history (status) VALUES ('validated')")
        history_id = cursor.lastrowid
        conn.commit()
        conn.close()

        sm = TweakStateMachine(history_id, "validated")
        
        with pytest.raises(ValueError):
            sm.transition("revert")

    def test_verified_at_only_on_verified(self, setup_test_db):
        conn = sqlite3.connect(TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tweak_history (status) VALUES ('applying')")
        history_id = cursor.lastrowid
        conn.commit()
        conn.close()

        sm = TweakStateMachine(history_id, "applying")
        
        sm.transition("verify_defer") 
        
        conn = sqlite3.connect(TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT verified_at FROM tweak_history WHERE id=?", (history_id,))
        verified_at = cursor.fetchone()[0]
        conn.close()
        
        assert verified_at is None