import pytest
from core.validation import TweakValidator, ValidationError

def test_mixed_verify_semantics():
    """TWEAK_RULES §7.1: Cannot mix verify_semantics"""
    v = TweakValidator()
    
    t1 = {
        "id": "a.test@1.0", "name": "A", "description": "", 
        "tier": 1, "risk_level": "low", "requires_reboot": False, 
        "rollback_guaranteed": True, "scope": ["registry"],
        "verify_semantics": "runtime",
        "actions": {"apply": []}
    }
    t2 = {
        "id": "b.test@1.0", "name": "B", "description": "", 
        "tier": 1, "risk_level": "low", "requires_reboot": False, 
        "rollback_guaranteed": True, "scope": ["registry"],
        "verify_semantics": "deferred",
        "verify_notes": "Requires service restart",
        "actions": {"apply": []}
    }
    
    with pytest.raises(ValidationError) as exc_info:
        v.validate_composition([t1, t2], [])
        
    assert "verify_semantics" in str(exc_info.value)

def test_non_guaranteed_rollback_batch():
    """TWEAK_RULES §4.2: Non-guaranteed must execute individually"""
    v = TweakValidator()
    
    t1 = {
        "id": "risk.test@1.0", "name": "Risky", "description": "", 
        "tier": 2, "risk_level": "medium", "requires_reboot": False, 
        "rollback_guaranteed": False, # Not guaranteed
        "rollback_limitations": ["one_way_operation"],
        "scope": ["filesystem"],
        "actions": {"apply": []}
    }
    t2 = {
        "id": "safe.test@1.0", "name": "Safe", "description": "", 
        "tier": 2, "risk_level": "medium", "requires_reboot": False, 
        "rollback_guaranteed": False, # Also not guaranteed
        "rollback_limitations": ["one_way_operation"],
        "scope": ["filesystem"],
        "actions": {"apply": []}
    }
    
    with pytest.raises(ValidationError) as exc_info:
        v.validate_composition([t1, t2], [])
        
    assert "individually" in str(exc_info.value).lower()

def test_tier3_batching_prohibited():
    """TWEAK_RULES §3.3: Tier 3 cannot be batched"""
    v = TweakValidator()
    
    t1 = {
        "id": "exp.a@1.0", "name": "ExpA", "description": "", 
        "tier": 3, "risk_level": "high", "requires_reboot": True, 
        "rollback_guaranteed": False, 
        "rollback_limitations": ["external_state"],
        "scope": ["boot"],
        "actions": {"apply": []}
    }
    t2 = {
        "id": "exp.b@1.0", "name": "ExpB", "description": "", 
        "tier": 3, "risk_level": "high", "requires_reboot": True, 
        "rollback_guaranteed": False, 
        "rollback_limitations": ["external_state"],
        "scope": ["boot"],
        "actions": {"apply": []}
    }
    
    with pytest.raises(ValidationError) as exc_info:
        v.validate_composition([t1, t2], [])
        
    assert "tier 3" in str(exc_info.value).lower()