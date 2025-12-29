from infra.executor import Executor
from infra.verify.actions import VerifyAction
from core.rollback import get_active_tweaks, get_snapshots_v2

class VerifyManager:
    def verify_all(self):
        executor = Executor(dry_run=True)

        invalid = []

        for entry in get_active_tweaks():
            snaps = get_snapshots_v2(entry["id"])

            for snap in snaps:
                action = VerifyAction(
                    snap["action_type"],
                    snap["metadata"]
                )

                ok = executor.execute(action)
                if not ok:
                    invalid.append(entry)
                    break

        return invalid
