import sqlite3
import core.rollback as rollback
from infra.recovery.detector import scan
from core.tweak_manager import TweakManager


class RecoveryManager:
    def recover(self) -> dict:
        zombies = scan()

        detected = len(zombies)
        recovered = 0
        failed = 0

        tm = TweakManager()

        for h in zombies:
            hid = h["id"]
            status = h["status"]

            try:
                if status in ("applying", "verifying", "failed"):
                    tm._execute_rollback_steps(hid)
                    rollback.clear_snapshots(hid)

                    conn = sqlite3.connect(rollback.DB_PATH)
                    conn.execute(
                        """
                        UPDATE tweak_history
                        SET status = 'reverted',
                            reverted_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (hid,),
                    )
                    conn.commit()
                    conn.close()

                elif status == "defined":
                    conn = sqlite3.connect(rollback.DB_PATH)
                    conn.execute(
                        """
                        UPDATE tweak_history
                        SET status = 'failed'
                        WHERE id = ?
                        """,
                        (hid,),
                    )
                    conn.commit()
                    conn.close()

                recovered += 1

            except Exception:
                failed += 1

        return {
            "detected": detected,
            "recovered": recovered,
            "failed": failed,
        }
