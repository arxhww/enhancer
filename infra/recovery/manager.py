from infra.recovery.detector import scan
import core.rollback as rollback


class RecoveryManager:
    def recover(self) -> list:
        zombies = scan()
        recovered = []

        for h in zombies:
            hid = h["id"]

            self._force_revert(hid)

            rollback.clear_snapshots(hid)

            recovered.append({
                "history_id": hid,
                "tweak_id": h["tweak_id"],
            })

        return recovered

    def _force_revert(self, history_id: int) -> None:
        import sqlite3
        from pathlib import Path

        db = Path(__file__).parents[2] / "enhancer.db"
        conn = sqlite3.connect(db, timeout=10.0)
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE tweak_history
            SET status = 'reverted',
                reverted_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (history_id,)
        )

        conn.commit()
        conn.close()
