import json
from pathlib import Path
from core.tweak_manager import TweakManager
import core.rollback as rollback

def test_reexplain_is_read_only(tmp_path):
    tweak = tmp_path / "tweak.json"
    tweak.write_text(json.dumps({
        "id": "test.reexplain@1.0",
        "name": "Explain Test",
        "tier": 1,
        "risk_level": "low",
        "requires_reboot": False,
        "rollback_guaranteed": True,
        "scope": ["registry"],
        "verify_semantics": "runtime",
        "actions": {
            "apply": [],
            "verify": []
        }
    }))

    manager = TweakManager()

    before = rollback.get_all()

    manager.reexplain(tweak)

    after = rollback.get_all()

    assert before == after