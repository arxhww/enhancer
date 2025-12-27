import json
from pathlib import Path
from typing import List

from . import rollback
from .actions.factory import create_action, create_action_from_snapshot
from .actions.verify_action import create_verify_action
from .actions.base import Action, ActionSnapshot
from .tweak_id import TweakID, validate_tweak_definition
from .recovery import mark_applying
from .validation import TweakValidator, ValidationError

class TweakManager:
    
    def __init__(self):
        self.validator = TweakValidator()
    
    def load_tweak(self, tweak_path: Path) -> dict:
        with open(tweak_path, 'r', encoding='utf-8') as f:
            tweak_def = json.load(f)
        
        try:
            self.validator.validate_definition(tweak_def)
        except ValidationError as e:
            print(f"[ERROR] Invalid Tweak Definition in {tweak_path.name}")
            print(f"  Reason: {e}")
            raise
            
        return tweak_def

    def apply(self, tweak_path: Path) -> bool:
        tweak = self.load_tweak(tweak_path)
        tweak_id = TweakID.parse(tweak["id"])
        
        active_tweaks_data = rollback.get_active_tweaks()
        active_ids = [t['tweak_id'] for t in active_tweaks_data]
        
        try:
            self.validator.validate_composition([tweak], active_ids)
        except ValidationError as e:
            print(f"[ERROR] Composition Check Failed")
            print(f"  Reason: {e}")
            return False

        return True
    
    def revert(self, tweak_id_str: str) -> bool:
        try:
            target_id = TweakID.parse(tweak_id_str)
            match_base_only = False
        except ValueError:
            if '.' in tweak_id_str and '@' not in tweak_id_str:
                match_base_only = True
                base_id = tweak_id_str
            else:
                print(f"Invalid tweak ID format: {tweak_id_str}")
                return False
        
        active_tweaks = rollback.get_active_tweaks()
        history_id = None
        
        for t in active_tweaks:
            active_id = TweakID.parse(t["tweak_id"])
            
            if match_base_only:
                if active_id.base_id == base_id:
                    history_id = t["id"]
                    target_id = active_id
                    break
            else:
                if active_id == target_id:
                    history_id = t["id"]
                    break
        
        if not history_id:
            print(f"No active tweak found for: {tweak_id_str}")
            return False
        
        print(f"\n[REVERT] Reverting tweak: {target_id}")
        try:
            self._rollback(history_id)
            rollback.mark_reverted(history_id)
            print(f"Tweak reverted successfully")
            return True
        except Exception as e:
            print(f"Error reverting tweak: {e}")
            return False
    
    def _rollback(self, history_id: int):
        snapshots = rollback.get_snapshots_v2(history_id)
        
        print(f"  Rolling back {len(snapshots)} actions...")
        
        for snap_dict in reversed(snapshots):
            snapshot = ActionSnapshot.from_dict(snap_dict)
            
            action = create_action_from_snapshot(snapshot)
            action.rollback(snapshot)
    
    def list_active(self):
        tweaks = rollback.get_active_tweaks()
        
        if not tweaks:
            print("\nNo active tweaks found.")
            return
        
        print("\n[ACTIVE TWEAKS]")
        for t in tweaks:
            try:
                tweak_id = TweakID.parse(t['tweak_id'])
                print(f"  • {tweak_id} (applied: {t['applied_at']})")
            except ValueError:
                print(f"  • {t['tweak_id']} (applied: {t['applied_at']})")