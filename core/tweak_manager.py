import json
from pathlib import Path
from typing import List, Tuple, Optional

from .executor import Executor

from . import rollback
from .actions.factory import create_action, create_action_from_snapshot
from .actions.verify_action import create_verify_action
from .actions.base import ActionSnapshot
from .tweak_id import TweakID
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
        self.validator.validate_definition(tweak_def)
        return tweak_def

    def apply(self, tweak_path: Path) -> bool:
        sm: Optional[TweakStateMachine] = None

        try:
            tweak = self.load_tweak(tweak_path)
            tweak_id = TweakID.parse(tweak["id"])

            active_ids = [t['tweak_id'] for t in rollback.get_active_tweaks()]
            self.validator.validate_composition([tweak], active_ids)

            if "verify" in tweak["actions"]:
                ok, _ = self._run_verify_phase(tweak["actions"]["verify"], is_precheck=True)
                if ok:
                    print("\n[NOOP] System already meets requirements.")
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
                verify_list = tweak["actions"].get("verify", [])
                if verify_list:
                    ok, _ = self._run_verify_phase(verify_list, is_precheck=False)
                    if not ok:
                        raise Exception("Post-apply verification failed")

                sm.transition("success")
                sm.transition("verify")
                rollback.mark_applied(history_id)
                return True

            sm.transition("verify_defer")
            rollback.mark_applied(history_id)
            return True

        except Exception as e:
            print(f"\n[ERROR] {e}")
            print("[INFO] Initiating Rollback...")
            try:
                if sm:
                    self._rollback_execution(sm.history_id)
                    sm.transition("fail", {"error_message": str(e)})
            except Exception as rb_err:
                print(f"[CRITICAL] Rollback Failed: {rb_err}")
                if sm:
                    sm.transition(
                        "fail",
                        {"error_message": f"Apply: {e} | Rollback: {rb_err}"}
                    )
            return False

    def _run_apply_phase(self, apply_actions_list: list) -> List[ActionSnapshot]:
        class ApplyStep:
            def __init__(self, action):
                self.action = action

            def execute(self):
                snap = self.action.snapshot()
                self.action.apply()
                return snap

        actions = [create_action(a) for a in apply_actions_list]
        steps = [ApplyStep(a) for a in actions]

        executor = Executor()
        return executor.run_steps(steps)

    def _run_verify_phase(
        self, verify_actions_list: list, is_precheck: bool
    ) -> Tuple[bool, str]:

        label = "PRE-CHECK" if is_precheck else "VERIFY"
        print(f"\n[{label}] Verifying state...")

        class VerifyStep:
            def __init__(self, action):
                self.action = action

            def execute(self):
                return self.action.verify()

        steps = [
            VerifyStep(create_verify_action(v))
            for v in verify_actions_list
        ]

        executor = Executor()
        results = executor.run_steps(steps)
        return all(r[0] for r in results), "Verification complete"

    def _rollback_execution(self, history_id: int):
        raw_snapshots = rollback.get_snapshots_v2(history_id)
        if not raw_snapshots:
            raise RuntimeError("Rollback invoked with zero snapshots")
        class RollbackStep:
            def __init__(self, action, snapshot):
                self.action = action
                self.snapshot = snapshot

            def execute(self):
                self.action.rollback(self.snapshot)

        steps = []
        for snap_dict in reversed(raw_snapshots):
            snapshot = ActionSnapshot.from_dict(snap_dict)
            action = create_action_from_snapshot(snapshot)
            steps.append(RollbackStep(action, snapshot))

        executor = Executor()
        executor.run_steps(steps)
        print("  Rollback completed successfully.")

    def _persist_schema_version(self, history_id: int, version: int):
        import sqlite3

        conn = sqlite3.connect(
            rollback.DB_PATH if hasattr(rollback, 'DB_PATH') else "enhancer.db"
        )
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tweak_history SET schema_version = ? WHERE id = ?",
                (version, history_id)
            )
            conn.commit()
        finally:
            conn.close()

    def list_active(self) -> None:
        tweaks = rollback.get_active_tweaks()
        if not tweaks:
            print("\nNo active tweaks found.")
            return

        print("\n[ACTIVE TWEAKS]")
        for t in tweaks:
            try:
                tid = TweakID.parse(t['tweak_id'])
                print(
                    f"  • {tid} "
                    f"(Status: {t.get('status', 'unknown')}, "
                    f"Applied: {t['applied_at']})"
                )
            except ValueError:
                print(f"  • {t['tweak_id']} (Status: {t.get('status', 'unknown')})")
    
    def _get_snapshots_for_recovery(self, history_id: int) -> list:
        return rollback.get_snapshots_v2(history_id)
    
    def revert(self, tweak_id_str: str) -> bool:
        try:
            tid = TweakID.parse(tweak_id_str)

            row = rollback.get_latest_history_by_tweak_id(str(tid))
            if not row:
                return False

            history_id, status = row

            if status == "reverted":
                return False

            rollback.mark_reverted(history_id)
            self._rollback_execution(history_id)
            rollback.clear_snapshots(history_id)

            return True

        except Exception:
            return False