from abc import ABC, abstractmethod
from typing import Any, Dict


class ActionSnapshot:
    
    def __init__(self, action_type: str, metadata: Dict[str, Any]) -> None:
        self.action_type = action_type
        self.metadata = metadata
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActionSnapshot':
        return cls(
            action_type=data["action_type"],
            metadata=data["metadata"]
        )


class Action(ABC):
    
    def __init__(self, definition: Dict[str, Any]) -> None:
        self.definition = definition
        self.action_type: str = definition["type"]
    
    @abstractmethod
    def snapshot(self) -> ActionSnapshot:
        pass
    
    @abstractmethod
    def apply(self) -> None:
        pass
    
    @abstractmethod
    def verify(self) -> bool:
        pass
    
    @abstractmethod
    def rollback(self, snapshot: ActionSnapshot) -> None:
        pass
    
    def get_description(self) -> str:
        return f"{self.action_type} action"
    
    @classmethod
    @abstractmethod
    def from_snapshot(cls, snapshot: ActionSnapshot) -> 'Action':
        pass