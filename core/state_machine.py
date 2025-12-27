import sqlite3
from datetime import datetime
from pathlib import Path
from .tweak_state import TweakState, can_transition, TRANSITIONS

DB_PATH = Path(__file__).parent.parent / "enhancer.db"

class TweakStateMachine:

    def __init__(self, history_id: int, current_state: str):
        self.history_id = history_id
        try:
            self.current_state = TweakState(current_state)
        except ValueError:
            self.current_state = TweakState.ORPHANED

    def transition(self, action: str, context: dict = None) -> TweakState:
        if not can_transition(self.current_state, action):
            valid = list(TRANSITIONS.get(self.current_state, {}).keys())
            raise ValueError(
                f"Invalid transition: {self.current_state.value} --[{action}]--> ?. "
                f"Valid actions from {self.current_state.value}: {valid}"
            )

        next_state = TRANSITIONS[self.current_state][action]
        self._persist_state(next_state, context)
        
        self.current_state = next_state
        return next_state

    def _persist_state(self, new_state: TweakState, context: dict = None):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        status_str = new_state.value
        
        cursor.execute("""
            UPDATE tweak_history
            SET status = ?
            WHERE id = ?
        """, (status_str, self.history_id))
        
        if context:
            if "error_message" in context:
                cursor.execute("""
                    UPDATE tweak_history
                    SET error_message = ?
                    WHERE id = ?
                """, (context["error_message"], self.history_id))
            
            if new_state == TweakState.VERIFIED:
                verified_at = context.get("verified_at", datetime.now())
                cursor.execute("""
                    UPDATE tweak_history
                    SET verified_at = ?
                    WHERE id = ?
                """, (verified_at, self.history_id))

        conn.commit()
        conn.close()