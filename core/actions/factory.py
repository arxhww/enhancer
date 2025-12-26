from typing import Dict, Any, Type
from .base import Action, ActionSnapshot
from .registry_action import RegistryAction
from .service_action import ServiceAction
from .powercfg_action import PowerCfgAction
from .bcdedit_action import BcdEditAction


# Registry of all available action types
ACTION_REGISTRY: Dict[str, Type[Action]] = {
    "registry": RegistryAction,
    "service": ServiceAction,
    "powercfg": PowerCfgAction,
    "bcdedit": BcdEditAction,
    # Future...
}


def create_action(definition: Dict[str, Any]) -> Action:
    action_type = definition.get("type")
    
    if not action_type:
        raise ValueError("Action definition missing 'type' field")
    
    action_class = ACTION_REGISTRY.get(action_type)
    
    if not action_class:
        available = ", ".join(ACTION_REGISTRY.keys())
        raise ValueError(
            f"Unknown action type: '{action_type}'. "
            f"Available types: {available}"
        )
    
    return action_class(definition)


def create_action_from_snapshot(snapshot: ActionSnapshot) -> Action:
    action_class = ACTION_REGISTRY.get(snapshot.action_type)
    
    if not action_class:
        raise ValueError(f"Unknown action type in snapshot: {snapshot.action_type}")
    
    return action_class.from_snapshot(snapshot)


def get_available_action_types() -> list:
    return list(ACTION_REGISTRY.keys())