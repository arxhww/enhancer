from typing import List, Dict, Optional
import sqlite3

from .rollback import DB_PATH, get_snapshots_v2
from .tweak_state import TweakState
from .state_machine import TweakStateMachine

class RecoveryManager:

    def scan(self) -> List[Dict]:
        rows = self._load_all_history()
        broken = []

        for row in rows:
            history_id = row["id"]
            state = TweakState(row["status"])
            snapshots = get_snapshots_v2(history_id)

            if self._is_invalid(state, snapshots):
                broken.append({
                    "id": history_id,
                    "state": state.value,
                    "snapshots": len(snapshots),
                })

        return broken

    def recover(self) -> int:
        broken = self.scan()
        fixed = 0

        for entry in broken:
            if self.recover_one(entry["id"]):
                fixed += 1

        return fixed

    def recover_one(self, history_id: int) -> bool:
        row = self._load_history(history_id)
        if not row:
            return False

        state = TweakState(row["status"])
        snapshots = get_snapshots_v2(history_id)

        target_state = self._decide_target_state(state, snapshots)
        if not target_state:
            return False

        self._force_state(history_id, target_state)
        return True


    def _is_invalid(self, state: TweakState, snapshots: list) -> bool:
        if state in (
            TweakState.VALIDATING,
            TweakState.APPLYING,
            TweakState.REVERTING,
        ):
            return True

        if state == TweakState.APPLIED and not snapshots:
            return True

        return False

    def _decide_target_state(
        self,
        state: TweakState,
        snapshots: list,
    ) -> Optional[TweakState]:

        if state in (TweakState.VALIDATING, TweakState.APPLYING):
            return TweakState.FAILED

        if state == TweakState.REVERTING:
            return TweakState.REVERTED if snapshots else TweakState.FAILED

        if state == TweakState.APPLIED and not snapshots:
            return TweakState.FAILED

        return None


    def _load_all_history(self) -> List[Dict]:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, status FROM tweak_history"
        )

        rows = cursor.fetchall()
        conn.close()

        return [{"id": r[0], "status": r[1]} for r in rows]

    def _load_history(self, history_id: int) -> Optional[Dict]:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, status FROM tweak_history WHERE id = ?",
            (history_id,)
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {"id": row[0], "status": row[1]}

    def _force_state(self, history_id: int, state: TweakState) -> None:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE tweak_history SET status = ? WHERE id = ?",
            (state.value, history_id)
        )

        conn.commit()
        conn.close()
