import pytest
import tempfile
from pathlib import Path
import json

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.tweak_manager import TweakManager
from core.rollback import init_db, DB_PATH as RDB_PATH

TEST_DB = Path(__file__).parent / "test_idempotency.db"

@pytest.fixture(autouse=True)
def isolated_db():
    import core.rollback as roll_mod
    original_path = roll_mod.DB_PATH
    
    roll_mod.DB_PATH = TEST_DB
    init_db()
    
    yield
    
    if TEST_DB.exists():
        TEST_DB.unlink()
    
    roll_mod.DB_PATH = original_path

def test_revert_twice_is_idempotent(isolated_db):
    m = TweakManager()
    
    t = {
        "id": "test.snapcleanup@1.0",
        "name": "Snapshot Cleanup Test",
        "description": "",
        "tier": 1,
        "risk_level": "low",
        "requires_reboot": False,
        "rollback_guaranteed": True,
        "scope": ["registry"],
        "schema_version": 1,
        "actions": {
            "apply": [
                {
                    "type": "registry",
                    "path": "HKCU\\Software\\Test",
                    "key": "SnapTest",
                    "value": 1,
                    "value_type": "DWORD",
                    "force_create": True
                }
            ]
        }
    }
    
    p = TEST_DB.parent / "snap.json"
    with open(p, 'w') as f:
        json.dump(t, f)
    
    m.apply(p)
    
    res1 = m.revert("test.snapcleanup@1.0")
    assert res1 is True
    
    res2 = m.revert("test.snapcleanup@1.0")
    assert res2 is True
    assert m.revert("test.snapcleanup@1.0") is True 
    
    print("[TEST] Idempotency validated.")