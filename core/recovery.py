import sqlite3
from pathlib import Path
from typing import Dict, List
from datetime import timedelta

from .time import DEFAULT_TIME_PROVIDER as TIME

DB_PATH = Path(__file__).parent.parent / "enhancer.db"


class RecoveryManager:
    """
    Strict recovery scanner and executor.

    Policy:
    - Recovery issues ONE command: rollback
    - Rollback is the single failure authority
    - Any rollback failure is fatal
    """

    def scan_for_issues(self) -> List[Dict]:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        issues: List[Dict] = []

        cursor.execute("""
            SELECT id, tweak_id, applied_at
            FROM tweak_history
            WHERE status IN ('pending', 'defined')
        """)
        for hid, tid, ts in cursor.fetchall():
            issues.append({
                "type": "stuck_pending",
                "history_id": hid,
                "tweak_id": tid,
                "applied_at": ts,
            })
        cutoff = TIME.now() - timedelta(minutes=5)
        cursor.execute("""
            SELECT id, tweak_id, applied_at
            FROM tweak_history
            WHERE status = 'applying'
        """)
        for hid, tid, ts in cursor.fetchall():
            issues.append({
                "type": "stuck_applying",
                "history_id": hid,
                "tweak_id": tid,
                "applied_at": ts,
            })

        conn.close()
        return issues

    def recover_all(self, manager) -> Dict:
        issues = self.scan_for_issues()

        results = {
            "issues_found": len(issues),
            "recovered": 0,
        }

        for issue in issues:
            if issue["type"] == "stuck_pending":
                self._mark_recovered(
                    issue["history_id"],
                    "Recovered from pending state (no execution)"
                )
                results["recovered"] += 1

            elif issue["type"] == "stuck_applying":
                try:
                    manager._rollback_execution(issue["history_id"])
                    
                    self._mark_recovered(
                        issue["history_id"],
                        "Recovered from applying state (rollback executed)"
                    )
                    results["recovered"] += 1
                except Exception as e:
                    raise RuntimeError(
                        f"Critical Recovery Failure for {issue['tweak_id']}: {e}"
                    ) from e

        return results

    def _mark_recovered(self, history_id: int, error_message: str) -> None:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE tweak_history
            SET status = 'recovered',
                error_message = ?
            WHERE id = ?
        """, (error_message, history_id))

        conn.commit()
        conn.close()