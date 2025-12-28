import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any

from .tweak_state import TweakState, TRANSITIONS
from .time import DEFAULT_TIME_PROVIDER as TIME

DB_PATH = Path(__file__).parent.parent / "enhancer.db"

class TweakStateMachine:

    def __init__(self, history_id: int):
        self.history_id = history_id

    def transition(self, action: str, context: Optional[Dict[str, Any]] = None) -> TweakState:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        try:
            conn.execute("BEGIN IMMEDIATE")

            cursor.execute("SELECT status FROM tweak_history WHERE id = ?", (self.history_id,))
            row = cursor.fetchone()

            if not row:
                raise AssertionError(f"ORPHANED history_id: {self.history_id}")

            current_state = TweakState(row[0])

            valid_actions = TRANSITIONS.get(current_state, {})
            if action not in valid_actions:
                valid = list(valid_actions.keys())
                raise AssertionError(
                    f"INVALID TRANSITION: {current_state.value} --[{action}]--> ? "
                    f"Valid: {valid}"
                )

            next_state = valid_actions[action]

            cursor.execute("""
                UPDATE tweak_history
                SET status = ?
                WHERE id = ?
            """, (next_state.value, self.history_id))

            if context:
                if "error_message" in context:
                    cursor.execute("""
                        UPDATE tweak_history
                        SET error_message = ?
                        WHERE id = ?
                    """, (context["error_message"], self.history_id))
                
                if "verified_at" in context:
                    cursor.execute("""
                        UPDATE tweak_history
                        SET verified_at = ?
                        WHERE id = ?
                    """, (context["verified_at"], self.history_id))

            if next_state == TweakState.REVERTED:
                cursor.execute("""
                    DELETE FROM snapshots_v2
                    WHERE history_id = ?
                """, (self.history_id,))
                print(f"  [CLEANUP] Snapshots consumed for history_id {self.history_id}.")

            conn.commit()
            return next_state

        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_current_state(self) -> TweakState:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT status FROM tweak_history WHERE id = ?", (self.history_id,))
            row = cursor.fetchone()
            if not row:
                return TweakState.ORPHANED
            return TweakState(row[0])
        finally:
            conn.close()