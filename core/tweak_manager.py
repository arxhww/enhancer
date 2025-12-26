import json
from pathlib import Path
from . import registry
from . import rollback

class TweakManager:
    
    def __init__(self):
        pass
    
    def load_tweak(self, tweak_path):
        with open(tweak_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def apply(self, tweak_path):
        tweak = self.load_tweak(tweak_path)
        tweak_id = tweak["id"]
        
        active_tweaks = rollback.get_active_tweaks()
        if any(t['tweak_id'] == tweak_id for t in active_tweaks):
            print(f"\nSKIP: Tweak '{tweak_id}' already active.")
            return False
        
        if "verify" in tweak["actions"]:
            print(f"\n[CHECK] Verifying current state of '{tweak_id}'...")
            if self._verify_actions(tweak["actions"]["verify"]):
                print(f"SKIP: System already meets requirements. (NOOP - Without history)")
                return True
        
        print(f"\n[TWEAK] Applying: {tweak['name']}")
        print(f"[INFO] {tweak['description']}")
        
        history_id = rollback.create_history_entry(tweak_id)
        
        try:
            print("\n[SNAPSHOT] Saving current state...")
            self._create_snapshots(history_id, tweak["actions"]["apply"])
            
            print("[APPLY] Applying changes (Strict Mode)...")
            self._execute_actions(tweak["actions"]["apply"])
            
            print("[VERIFY] Verifying changes...")
            if self._verify_actions(tweak["actions"]["verify"]):
                rollback.mark_success(history_id)
                print(f"\nTweak '{tweak['name']}' applied correctly")
                return True
            else:
                raise Exception("Verification failed after applying tweak.")
                
        except Exception as e:
            print(f"\nError applying tweak: {e}")
            self._rollback(history_id)
            rollback.mark_rolled_back(history_id, str(e))
            return False
    
    def revert(self, tweak_id):
        active_tweaks = rollback.get_active_tweaks()
        history_id = None
        for t in active_tweaks:
            if t["tweak_id"] == tweak_id:
                history_id = t["id"]
                break
        
        if not history_id:
            print(f"No active tweak found with ID: {tweak_id}")
            return False

        print(f"\n[REVERT] Reverting tweak: {tweak_id}")
        try:
            self._rollback(history_id)
            rollback.mark_reverted(history_id)
            print(f"Tweak reverted correctly")
            return True
        except Exception as e:
            print(f"Error reverting tweak: {e}")
            return False
    
    def _create_snapshots(self, history_id, actions):
        for action in actions:
            if action["type"] == "registry":
                path = action["path"]
                key = action["key"]
                subkey_existed = registry.subkey_exists(path)
                old_value, old_type = registry.get_value(path, key)
                
                value_existed = old_type is not None
                
                rollback.save_snapshot(
                    history_id, 
                    path, 
                    key, 
                    old_value, 
                    old_type,
                    value_existed,
                    subkey_existed
                )
    
    def _execute_actions(self, actions):
        for action in actions:
            if action["type"] == "registry":
                registry.set_value(
                    action["path"],
                    action["key"],
                    action["value"],
                    action.get("value_type", "DWORD"),
                    force=False 
                )
    
    def _verify_actions(self, verifications):
        success = True
        for verify in verifications:
            if verify["type"] == "registry":
                actual_value, _ = registry.get_value(verify["path"], verify["key"])
                expected_value = verify["expected"]
                
                if actual_value is None:
                    print(f"  Verification failed in {verify['path']}: Value or path does not exist.")
                    success = False
                elif actual_value != expected_value:
                    print(f"  Verification failed in {verify['key']}: Expected {expected_value}, Got {actual_value}")
                    success = False
        
        return success
    
    def _rollback(self, history_id):
        snapshots = rollback.get_snapshots(history_id)
        
        for snap in reversed(snapshots):
            if snap["value_existed"]:
                registry.set_value(
                    snap["path"],
                    snap["key"],
                    snap["value"],
                    snap["type"],
                    force=True 
                )
            else:
                registry.delete_value(snap["path"], snap["key"])
                if not snap["subkey_existed"]:
                    registry.delete_subkey(snap["path"])
    
    def list_active(self):
        tweaks = rollback.get_active_tweaks()
        
        if not tweaks:
            print("No active tweaks found.")
            return
        
        print("\n[ACTIVE TWEAKS]")
        for t in tweaks:
            print(f"  • {t['tweak_id']} (applied: {t['applied_at']})")