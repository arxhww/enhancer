import json
from pathlib import Path
from typing import List, Tuple, Optional

from . import rollback
from .actions.factory import create_action, create_action_from_snapshot
from .actions.verify_action import create_verify_action
from .actions.base import Action, ActionSnapshot
from .tweak_id import TweakID, validate_tweak_definition
from .tweak_state import TweakState
from .state_machine import TweakStateMachine
from .validation import TweakValidator, ValidationError
from .constants import SCHEMA_VERSION
from .migrations import migrate_to_v2

class TweakManager:
    
    def __init__(self):
        self.validator = TweakValidator()
        try:
            migrate_to_v2()
        except Exception as e:
            print(f"[WARN] Database migration issue: {e}")
    
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
        sm: Optional[TweakStateMachine] = None
        
        try:
            tweak = self.load_tweak(tweak_path)
            tweak_id = TweakID.parse(tweak["id"])
            
            active_ids = [t['tweak_id'] for t in rollback.get_active_tweaks()]
            try:
                self.validator.validate_composition([tweak], active_ids)
            except ValidationError as e:
                print(f"[ERROR] Composition Check Failed: {e}")
                return False

            if "verify" in tweak["actions"]:
                is_verified, _ = self._run_verify_phase(tweak["actions"]["verify"], is_precheck=True)
                
                if is_verified:
                    print(f"\n[NOOP] System already meets requirements.")
                    return True

            history_id = rollback.create_history_entry(str(tweak_id))
            self._persist_schema_version(history_id, SCHEMA_VERSION)
            sm = TweakStateMachine(history_id, "defined")
            
            sm.transition("validate") 

            sm.transition("apply") 
            
            snapshots = self._run_apply_phase(tweak["actions"]["apply"])
            
            for snap in snapshots:
                rollback.save_snapshot_v2(history_id, snap)

            v_sem = tweak.get("verify_semantics", "runtime")
            
            if v_sem == "runtime":
                verify_list = tweak["actions"].get("verify")
                
                if verify_list:
                    success, _ = self._run_verify_phase(verify_list, is_precheck=False)
                    if success:
                        sm.transition("success")   
                        sm.transition("verify")   
                        print(f"\n[SUCCESS] Tweak '{tweak['name']}' applied and verified.")
                        return True
                    else:
                        raise Exception("Post-apply verification failed")
                else:
                    sm.transition("success")
                    print(f"\n[SUCCESS] Tweak '{tweak['name']}' applied (no explicit verify defined).")
                    return True
            else:
                sm.transition("verify_defer")
                print(f"\n[SUCCESS] Tweak applied. Verification deferred.")
                return True

        except ValueError as e:
            print(f"[CRITICAL] State Machine Error: {e}")
            if sm: sm.transition("fail", {"error_message": str(e)})
            return False
            
        except Exception as e:
            print(f"\n[ERROR] {e}")
            print(f"[INFO] Initiating Rollback...")
            
            try:
                if sm:
                    self._rollback_execution(sm.history_id)
                    sm.transition("fail", {"error_message": str(e)})
            except Exception as rb_err:
                print(f"[CRITICAL] Rollback Failed: {rb_err}")
                if sm: sm.transition("fail", {"error_message": f"Apply: {e} | Rollback: {rb_err}"})
            
            return False

    def _run_verify_phase(self, verify_actions_list: list, is_precheck: bool) -> Tuple[bool, str]:
        label = "PRE-CHECK" if is_precheck else "VERIFY"
        print(f"\n[{label}] Verifying state...")
        
        actions = [create_verify_action(v) for v in verify_actions_list]
        results = []
        
        for i, action in enumerate(actions, 1):
            desc = action.get_description()
            res = action.verify()
            results.append(res)
            status = "✓" if res else "✗"
            print(f"  [{i}/{len(actions)}] {desc} ... {status}")
            
        return all(results), "Verification complete"

    def _run_apply_phase(self, apply_actions_list: list) -> List[ActionSnapshot]:
        print(f"\n[APPLY] Executing {len(apply_actions_list)} actions...")
        
        actions = [create_action(a) for a in apply_actions_list]
        snapshots = []
        
        for i, action in enumerate(actions, 1):
            print(f"  [{i}/{len(actions)}] {action.get_description()}")
            
            snap = action.snapshot()
            snapshots.append(snap)
            
            action.apply()
            
        return snapshots

    def _rollback_execution(self, history_id: int):
        raw_snapshots = rollback.get_snapshots_v2(history_id)
        print(f"  Rolling back {len(raw_snapshots)} actions...")
        
        for snap_dict in reversed(raw_snapshots):
            snapshot_obj = ActionSnapshot.from_dict(snap_dict)
            action = create_action_from_snapshot(snapshot_obj)
            action.rollback(snapshot_obj)
            
        print("  Rollback completed successfully.")

    def _persist_schema_version(self, history_id: int, version: int):
        import sqlite3
        conn = sqlite3.connect(rollback.DB_PATH if hasattr(rollback, 'DB_PATH') else "enhancer.db")
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE tweak_history SET schema_version = ? WHERE id = ?", (version, history_id))
            conn.commit()
        finally:
            conn.close()

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
        target_entry = None
        
        for t in active_tweaks:
            active_id = TweakID.parse(t["tweak_id"])
            
            is_match = False
            if match_base_only:
                if active_id.base_id == base_id: is_match = True
            else:
                if active_id == target_id: is_match = True
            
            if is_match:
                history_id = t["id"]
                target_entry = t
                target_id = active_id
                break
        
        if not history_id:
            print(f"No active tweak found for: {tweak_id_str}")
            return False
        
        print(f"\n[REVERT] Reverting tweak: {target_id}")
        
        sm = TweakStateMachine(history_id, target_entry.get('status', 'unknown'))
        
        try:
            self._rollback_execution(history_id)
            sm.transition("revert") 
            rollback.mark_reverted(history_id) 
            print(f"Revert completed successfully.")
            return True
        except ValueError as e:
            print(f"[ERROR] Invalid state for revert: {e}")
            return False
        except Exception as e:
            print(f"[ERROR] Revert failed: {e}")
            return False

    def list_active(self):
        tweaks = rollback.get_active_tweaks()
        if not tweaks:
            print("\nNo active tweaks found.")
            return
        print("\n[ACTIVE TWEAKS]")
        for t in tweaks:
            try:
                tid = TweakID.parse(t['tweak_id'])
                print(f"  • {tid} (Status: {t.get('status', 'unknown')}, Applied: {t['applied_at']})")
            except ValueError:
                print(f"  • {t['tweak_id']} (Status: {t.get('status', 'unknown')})")