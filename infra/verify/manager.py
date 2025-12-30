from core.rollback import get_active_tweaks
from core.tweak_manager import TweakManager

class VerifyManager:
    def verify_all(self):
        tm = TweakManager()
        active = get_active_tweaks()

        results = []
        for t in active:
            ok = tm.verify(t["tweak_id"])
            results.append(ok)

        return all(results)
