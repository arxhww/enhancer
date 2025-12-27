import pytest
from core.validation import TweakValidator, ValidationError
from core.constants import SCHEMA_VERSION

class TestSchemaValidation:
    
    def test_valid_minimal_tweak(self):
        definition = {
            "id": "test.tweak@1.0",
            "name": "Test Tweak",
            "description": "A test",
            "tier": 1,
            "risk_level": "low",
            "requires_reboot": False,
            "rollback_guaranteed": True,
            "scope": ["registry"],
            "schema_version": SCHEMA_VERSION,
            "actions": {"apply": []}
        }
        v = TweakValidator()
        v.validate_definition(definition) 

    def test_invalid_schema_version(self):
        definition = {
            "id": "test.old@1.0",
            "name": "Old",
            "description": "Old",
            "tier": 1,
            "risk_level": "low",
            "requires_reboot": False,
            "rollback_guaranteed": True,
            "scope": ["registry"],
            "schema_version": 99, 
            "actions": {"apply": []}
        }
        v = TweakValidator()
        with pytest.raises(ValidationError):
            v.validate_definition(definition)
        
        with pytest.raises(ValidationError) as exc_info:
            v.validate_definition(definition)
        
        assert isinstance(exc_info.value, ValidationError)
        assert "version" in str(exc_info.value).lower()

    def test_tier3_requires_high_risk(self):
        definition = {
            "id": "exp.danger@1.0",
            "name": "Exp",
            "description": "X",
            "tier": 3,
            "risk_level": "low", 
            "requires_reboot": True,
            "rollback_guaranteed": False,
            "rollback_limitations": ["one_way"],
            "scope": ["boot"],
            "schema_version": SCHEMA_VERSION,
            "actions": {"apply": []}
        }
        v = TweakValidator()
        with pytest.raises(ValidationError):
            v.validate_definition(definition)

    def test_boot_requires_reboot(self):
        definition = {
            "id": "boot.fail@1.0",
            "name": "Boot",
            "description": "X",
            "tier": 2,
            "risk_level": "medium",
            "requires_reboot": False, 
            "rollback_guaranteed": True,
            "scope": ["boot"],
            "schema_version": SCHEMA_VERSION,
            "actions": {"apply": []}
        }
        v = TweakValidator()
        with pytest.raises(ValidationError):
            v.validate_definition(definition)
            
    def test_deferred_requires_notes(self):
        definition = {
            "id": "defer.no@1.0",
            "name": "Deferred",
            "description": "X",
            "tier": 1,
            "risk_level": "low",
            "requires_reboot": False,
            "rollback_guaranteed": True,
            "scope": ["registry"],
            "verify_semantics": "deferred", 
            "schema_version": SCHEMA_VERSION,
            "actions": {"apply": []}
        }
        v = TweakValidator()
        with pytest.raises(ValidationError):
            v.validate_definition(definition)


class TestCompositionValidation:
    
    def test_mixed_tiers_rejected(self):
        v = TweakValidator()
        t1 = {
            "id": "a.test@1.0", "name": "A", "description": "", 
            "tier": 1, "risk_level": "low", "requires_reboot": False, 
            "rollback_guaranteed": True, "scope": ["registry"], "schema_version": SCHEMA_VERSION,
            "actions": {"apply": []}
        }
        t2 = {
            "id": "b.test@1.0", "name": "B", "description": "", 
            "tier": 2, "risk_level": "medium", "requires_reboot": False, 
            "rollback_guaranteed": True, "scope": ["registry"], "schema_version": SCHEMA_VERSION,
            "actions": {"apply": []}
        }
        
        with pytest.raises(ValidationError):
            v.validate_composition([t1, t2], [])

    def test_mixed_verify_semantics_rejected(self):
        v = TweakValidator()
        t1 = {
            "id": "a.test@1.0", "name": "A", "description": "", 
            "tier": 1, "risk_level": "low", "requires_reboot": False, 
            "rollback_guaranteed": True, "scope": ["registry"], "schema_version": SCHEMA_VERSION,
            "verify_semantics": "runtime", "actions": {"apply": []}
        }
        t2 = {
            "id": "b.test@1.0", "name": "B", "description": "", 
            "tier": 1, "risk_level": "low", "requires_reboot": False, 
            "rollback_guaranteed": True, "scope": ["registry"], "schema_version": SCHEMA_VERSION,
            "verify_semantics": "deferred", "verify_notes": "Wait for reboot", "actions": {"apply": []}
        }
        
        with pytest.raises(ValidationError) as exc:
            v.validate_composition([t1, t2], [])
        
        assert isinstance(exc.value, ValidationError)
        assert "verify" in str(exc.value).lower()

    def test_tier3_must_be_individual(self):
        v = TweakValidator()
        t1 = {
            "id": "experimental.one@1.0", "name": "E1", "description": "", 
            "tier": 3, "risk_level": "high", "requires_reboot": True, 
            "rollback_guaranteed": False, "rollback_limitations": ["external"], 
            "scope": ["boot"], "schema_version": SCHEMA_VERSION,
            "actions": {"apply": []}
        }
        t2 = {
            "id": "experimental.two@1.0", "name": "E2", "description": "", 
            "tier": 3, "risk_level": "high", "requires_reboot": True, 
            "rollback_guaranteed": False, "rollback_limitations": ["external"], 
            "scope": ["boot"], "schema_version": SCHEMA_VERSION,
            "actions": {"apply": []}
        }
        
        with pytest.raises(ValidationError) as exc:
            v.validate_composition([t1, t2], [])
        assert "tier 3" in str(exc.value).lower()

    def test_non_guaranteed_rollback_isolation(self):
        v = TweakValidator()
        t1 = {
            "id": "risk.one@1.0", "name": "R1", "description": "", 
            "tier": 2, "risk_level": "medium", "requires_reboot": False, 
            "rollback_guaranteed": False, "rollback_limitations": ["one_way"],
            "scope": ["filesystem"], "schema_version": SCHEMA_VERSION,
            "actions": {"apply": []}
        }
        t2 = {
            "id": "risk.two@1.0", "name": "R2", "description": "", 
            "tier": 2, "risk_level": "medium", "requires_reboot": False, 
            "rollback_guaranteed": False, "rollback_limitations": ["one_way"],
            "scope": ["filesystem"], "schema_version": SCHEMA_VERSION,
            "actions": {"apply": []}
        }
        
        with pytest.raises(ValidationError) as exc:
            v.validate_composition([t1, t2], [])
        assert "individually" in str(exc.value).lower()

    def test_conflicts_block_apply(self):
        v = TweakValidator()
        
        active_ids = ["performance.disable_superfetch@1.0"]
        
        t_b = {
            "id": "performance.enable_superfetch@1.0", "name": "Enable", "description": "", 
            "tier": 1, "risk_level": "low", "requires_reboot": False, 
            "rollback_guaranteed": True, "scope": ["registry"], "schema_version": SCHEMA_VERSION,
            "conflicts_with": ["performance.disable_superfetch@1.0"],
            "actions": {"apply": []}
        }
        
        with pytest.raises(ValidationError) as exc:
            v.validate_composition([t_b], active_ids)
        assert "conflict" in str(exc.value).lower()

    def test_dependency_satisfied(self):
        v = TweakValidator()
        
        active_ids = ["privacy.disable_search@1.0"]
        
        t = {
            "id": "privacy.disable_cortana@1.0", "name": "Cortana", "description": "", 
            "tier": 1, "risk_level": "low", "requires_reboot": False, 
            "rollback_guaranteed": True, "scope": ["registry"], "schema_version": SCHEMA_VERSION,
            "dependencies": ["privacy.disable_search@1.0"],
            "actions": {"apply": []}
        }
        
        v.validate_composition([t], active_ids)

    def test_dependency_unsatisfied_blocks(self):
        v = TweakValidator()
        
        active_ids = [] 
        
        t = {
            "id": "privacy.disable_cortana@1.0", "name": "Cortana", "description": "", 
            "tier": 1, "risk_level": "low", "requires_reboot": False, 
            "rollback_guaranteed": True, "scope": ["registry"], "schema_version": SCHEMA_VERSION,
            "dependencies": ["privacy.disable_search@1.0"],
            "actions": {"apply": []}
        }
        
        with pytest.raises(ValidationError) as exc:
            v.validate_composition([t], active_ids)
        assert "dependency" in str(exc.value).lower()