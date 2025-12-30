from core.tweak_manager import TweakManager
from core.rollback import get_active_tweaks

def test_apply_crash_leaves_no_zombies():
    tm = TweakManager()
    try:
        tm.apply("tests/test_tweaks/minimal.json")
    except Exception:
        pass

    assert get_active_tweaks() == []
