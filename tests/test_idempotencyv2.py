from core.tweak_manager import TweakManager

def test_recover_is_idempotent():
    tm = TweakManager()
    tm.recover("non.existent@1.0")
    tm.recover("non.existent@1.0")
