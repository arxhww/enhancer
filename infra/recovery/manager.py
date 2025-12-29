from infra.recovery.detector import scan
import core.rollback as rollback
from core.state_machine import TweakStateMachine

class RecoveryManager:
    def recover(self) -> list:
        zombies = scan()
        recovered = []

        for h in zombies:
            history_id = h["id"]
            sm = TweakStateMachine(history_id)

            sm.transition("fail", {
                "error_message": "recovered from zombie state"
            })

            sm.transition("revert")
            sm.transition("success")

            recovered.append(history_id)

        return recovered
