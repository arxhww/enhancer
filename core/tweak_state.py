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
    REVERTING = "reverting" 
    REVERTED = "reverted"  
    ORPHANED = "orphaned"

TRANSITIONS: Dict['TweakState', Dict[str, 'TweakState']] = {
    TweakState.DEFINED: {
        "validate": TweakState.VALIDATED,
        "apply_success": TweakState.APPLIED,
    },
    TweakState.VALIDATED: {
        "apply": TweakState.APPLYING,
    },
    TweakState.APPLYING: {
        "success": TweakState.APPLIED,
        "apply_success": TweakState.APPLIED, 
        "fail": TweakState.FAILED,
    },
    TweakState.APPLIED: {
        "verify": TweakState.VERIFIED,
        "revert": TweakState.REVERTING,
    },
    TweakState.APPLIED_UNVERIFIED: {
        "verify": TweakState.VERIFIED,
        "revert": TweakState.REVERTING,
    },
    TweakState.VERIFIED: {
        "revert": TweakState.REVERTING,
    },
    TweakState.FAILED: {
        "revert": TweakState.REVERTING,
    },
    TweakState.REVERTING: {
        "success": TweakState.REVERTED,
        "fail": TweakState.FAILED,
    },
    TweakState.REVERTED: {}, 
    TweakState.ORPHANED: {},
}

def can_transition(state: TweakState, action: str) -> bool:
    return action in TRANSITIONS.get(state, {})
