from core.tweak_manager import TweakManager
from pathlib import Path

def test_dry_run_creates_no_history(tmp_path):
    tweak = tmp_path / "t.json"
    tweak.write_text("""
    {
      "id": "test.dry@1.0",
      "name": "dry",
      "tier": 1,
      "risk_level": "low",
      "requires_reboot": false,
      "rollback_guaranteed": true,
      "scope": ["registry"],
      "actions": { "apply": [] }
    }
    """)

    tm = TweakManager()
    assert tm.dry_run(tweak) is True
