from typing import Any, Dict

from .base import Action, ActionSnapshot
from .. import registry


class RegistryVerifyAction(Action):
    
    def __init__(self, definition: Dict[str, Any]) -> None:
        super().__init__(definition)
        
        self.path: str = definition["path"]
        self.key: str = definition["key"]
        self.expected: Any = definition["expected"]
        self.expected_type: str | None = definition.get("expected_type", None)
    
    def snapshot(self) -> ActionSnapshot:
        raise NotImplementedError(
            "Verify actions are read-only and do not create snapshots. "
            "This method should never be called."
        )
    
    def apply(self) -> None:
        raise NotImplementedError(
            "Verify actions are read-only and do not modify system state."
        )
    
    def verify(self) -> bool:
        actual_value, actual_type = registry.get_value(self.path, self.key)
        
        if actual_value is None:
            return False
        
        if actual_value != self.expected:
            return False
        
        if self.expected_type is not None:
            expected_type_code = registry.REG_TYPES.get(
                self.expected_type, 
                self.expected_type
            )
            if actual_type != expected_type_code:
                return False
        
        return True
    
    def rollback(self, snapshot: ActionSnapshot) -> None:
        raise NotImplementedError(
            "Verify actions are read-only and cannot be rolled back."
        )
    
    def get_description(self) -> str:
        return f"Verify {self.path}\\{self.key} == {self.expected}"
    
    @classmethod
    def from_snapshot(cls, snapshot: ActionSnapshot) -> 'RegistryVerifyAction':
        raise NotImplementedError(
            "Verify actions do not participate in rollback and cannot be "
            "deserialized from snapshots."
        )


def create_verify_action(definition: Dict[str, Any]) -> Action:
    action_type = definition.get("type")
    
    if action_type == "registry":
        return RegistryVerifyAction(definition)
    
    # Future: service_verify, powercfg_verify, etc.
    
    raise ValueError(
        f"Unknown verify action type: '{action_type}'. "
        f"Available verify types: registry"
    )