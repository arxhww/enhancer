import json
from pathlib import Path
from typing import List

from . import rollback
from .actions.factory import create_action, create_action_from_snapshot
from .actions.verify_action import create_verify_action
from .actions.base import Action, ActionSnapshot
from .tweak_id import TweakID, validate_tweak_definition
from .recovery import mark_applying


class TweakManager:
    
    def __init__(self):
        pass
    
    def load_tweak(self, tweak_path: Path) -> dict:
        with open(tweak_path, 'r', encoding='utf-8') as f:
            tweak_def = json.load(f)
        
        validate_tweak_definition(tweak_def)
        
        return tweak_def
    
    def apply(self, tweak_path: Path) -> bool:
        tweak = self.load_tweak(tweak_path)
        tweak_id = TweakID.parse(tweak["id"])
        
        active_tweaks = rollback.get_active_tweaks()
        for t in active_tweaks:
            existing_id = TweakID.parse(t['tweak_id'])
            if existing_id.base_id == tweak_id.base_id:
                print(f"\n[SKIP] Tweak base '{tweak_id.base_id}' already active (version {existing_id.version})")
                print(f"  Revert first if you want to apply version {tweak_id.version}")
                return False
        
        if "verify" in tweak["actions"]:
            print(f"\n[PRE-CHECK] Verifying current state of '{tweak_id}'...")
            
            verify_actions = [
                create_verify_action(v) for v in tweak["actions"]["verify"]
            ]
            
            all_verified = all(action.verify() for action in verify_actions)
            
            if all_verified:
                print(f"[SKIP] System already meets requirements")
                
                history_id = rollback.create_history_entry(str(tweak_id))
                rollback.mark_noop(history_id)
                
                return True
        
        print(f"\n[TWEAK] Applying: {tweak['name']}")
        print(f"[INFO] {tweak['description']}")
        print(f"[ID] {tweak_id}")
        
        history_id = rollback.create_history_entry(str(tweak_id))
        
        try:
            mark_applying(history_id)
            
            apply_actions = [create_action(a) for a in tweak["actions"]["apply"]]
            
            print(f"\n[SNAPSHOT] Capturing current state ({len(apply_actions)} actions)...")
            snapshots: List[ActionSnapshot] = []
            for i, action in enumerate(apply_actions, 1):
                print(f"  [{i}/{len(apply_actions)}] {action.get_description()}")
                snap = action.snapshot()
                snapshots.append(snap)
                rollback.save_snapshot_v2(history_id, snap)
            
            print(f"\n[APPLY] Executing changes...")
            for i, action in enumerate(apply_actions, 1):
                print(f"  [{i}/{len(apply_actions)}] {action.get_description()}")
                action.apply()
            
            print(f"\n[VERIFY] Verifying results...")
            for i, action in enumerate(apply_actions, 1):
                if not action.verify():
                    raise Exception(
                        f"Verification failed for action {i}: {action.get_description()}"
                    )
                print(f"  [{i}/{len(apply_actions)}] ✓")
            
            rollback.mark_success(history_id)
            print(f"\nTweak '{tweak['name']}' applied successfully")
            return True
            
        except Exception as e:
            print(f"\nError applying tweak: {e}")
            print(f"[ROLLBACK] Reverting changes...")
            
            try:
                self._rollback(history_id)
                rollback.mark_rolled_back(history_id, str(e))
                print(f"Rollback completed successfully")
            except Exception as rb_error:
                print(f"CRITICAL: Rollback also failed: {rb_error}")
                rollback.mark_rolled_back(history_id, f"Apply failed: {e} | Rollback failed: {rb_error}")
            
            return False
    
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