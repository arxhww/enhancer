from enum import Enum
from typing import Dict

class TweakState(Enum):
    DEFINED = "defined"
    VALIDATED = "validated"
    APPLYING = "applying"
    APPLIED = "applied"
    APPLIED_UNVERIFIED = "applied_unverified"
    VERIFIED = "verified"
    FAILED = "failed"
    REVERTED = "reverted"
    ORPHANED = "orphaned"

TRANSITIONS: Dict['TweakState', Dict[str, 'TweakState']] = {
    TweakState.DEFINED: {
        "validate": TweakState.VALIDATED,
    },
    TweakState.VALIDATED: {
        "apply": TweakState.APPLYING,
    },
    TweakState.APPLYING: {
        "success": TweakState.APPLIED,
        "verify_defer": TweakState.APPLIED_UNVERIFIED,
        "fail": TweakState.FAILED,
    },
    TweakState.APPLIED: {
        "verify": TweakState.VERIFIED,
        "revert": TweakState.REVERTED,
    },
    TweakState.APPLIED_UNVERIFIED: {
        "verify": TweakState.VERIFIED,
        "revert": TweakState.REVERTED,
    },
    TweakState.VERIFIED: {
        "revert": TweakState.REVERTED,
    },
    TweakState.FAILED: {
        "revert": TweakState.REVERTED 
    },
    TweakState.REVERTED: {
    },
    TweakState.ORPHANED: {} 
}

def can_transition(current: TweakState, action: str) -> bool:
    valid_actions = TRANSITIONS.get(current)
    if not valid_actions:
        return False
    return action in valid_actions