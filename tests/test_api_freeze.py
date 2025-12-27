import inspect
import pytest
from pathlib import Path

from core.tweak_manager import TweakManager
from core.validation import TweakValidator, ValidationError
from core.recovery import RecoveryManager
from core.constants import SCHEMA_VERSION, ENGINE_VERSION

class TestPublicAPI:
    """Ensures the public API defined in API_FREEZE.md remains stable."""
    
    def test_tweak_manager_exists(self):
        assert TweakManager is not None

    def test_tweak_manager_apply_signature(self):
        """Verify apply(tweak_path: Path) -> bool"""
        sig = inspect.signature(TweakManager.apply)
        params = list(sig.parameters.keys())
        assert params == ['self', 'tweak_path']
        assert sig.return_annotation == bool

    def test_tweak_manager_revert_signature(self):
        """Verify revert(tweak_id_str: str) -> bool"""
        sig = inspect.signature(TweakManager.revert)
        params = list(sig.parameters.keys())
        assert params == ['self', 'tweak_id_str']
        assert sig.return_annotation == bool

    def test_tweak_manager_list_active_signature(self):
        """Verify list_active() -> None"""
        sig = inspect.signature(TweakManager.list_active)
        params = list(sig.parameters.keys())
        # Note: 'self' is included by inspect
        assert params == ['self'] 
        assert sig.return_annotation is None # Returns None (void)

    def test_validator_validate_definition_signature(self):
        sig = inspect.signature(TweakValidator.validate_definition)
        params = list(sig.parameters.keys())
        assert params == ['self', 'definition']
        assert sig.return_annotation is None

    def test_validator_validate_composition_signature(self):
        sig = inspect.signature(TweakValidator.validate_composition)
        params = list(sig.parameters.keys())
        assert params == ['self', 'batch', 'active_tweak_ids']
        assert sig.return_annotation is None

    def test_recovery_manager_interface(self):
        assert RecoveryManager is not None
        sig = inspect.signature(RecoveryManager.recover_all)
        # We just check it exists and takes 'manager' arg
        params = list(sig.parameters.keys())
        assert 'manager' in params

    def test_constants_exist(self):
        assert SCHEMA_VERSION == 1
        assert ENGINE_VERSION == "1.2.0"

    def test_validation_error_is_public(self):
        assert ValidationError is not None
        assert issubclass(ValidationError, Exception)