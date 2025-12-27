import pytest
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.tweak_manager import TweakManager
from core.rollback import get_active_tweaks

MOCK_TWEAK_DEF = {
    "id": "test.idempotency@1.0",
    "name": "Idempotency Test",
    "description": "Test",
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
                "path": "HKEY_CURRENT_USER\\Software\\EnhancerTest",
                "key": "TestKey",
                "value": 1,
                "value_type": "DWORD",
                "force_create": True
            }
        ]
    }
}

@pytest.fixture
def temp_tweak_file(tmp_path):
    import json
    file = tmp_path / "test_idempotency.json"
    with open(file, 'w') as f:
        json.dump(MOCK_TWEAK_DEF, f)
    return file

@pytest.fixture
def manager():
    return TweakManager()

def test_apply_is_idempotent(manager, temp_tweak_file):

    success1 = manager.apply(temp_tweak_file)
    assert success1 is True
    
    success2 = manager.apply(temp_tweak_file)
    
    assert success2 is True

def test_revert_is_idempotent(manager, temp_tweak_file):

    manager.apply(temp_tweak_file)
    
    success1 = manager.revert("test.idempotency@1.0")
    assert success1 is True
    
    success2 = manager.revert("test.idempotency@1.0")
    assert success2 is False 

def test_verify_action_idempotency():
    from core.actions.registry_action import RegistryAction
    from core.actions.verify_action import RegistryVerifyAction
    
    action = RegistryAction(MOCK_TWEAK_DEF["actions"]["apply"][0])
    
    try:
        action.apply() 
        val1, _ = action.verify() 
        val2, _ = action.verify() 
        assert val1 == val2 
    finally:
        snap = action.snapshot()
        action.rollback(snap)