import json
import sqlite3
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
from .validation import TweakValidator
from .constants import SCHEMA_VERSION
from .migrations import migrate_to_v2


class TweakManager:

    def __init__(self):
        self.validator = TweakValidator()
        self._rollback_execution = self._execute_rollback_steps

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
            tweak_id = tweak["id"]
            
            active_ids = [t['tweak_id'] for t in rollback.get_active_tweaks()]
            self.validator.validate_composition([tweak], active_ids)

            verify_list = tweak["actions"].get("verify", [])
            if verify_list:
                ok, _ = self._run_verify_phase(verify_list, is_precheck=True)
                if ok:
                    print("\n[NOOP] System already meets requirements.")
                    return True

            history_id = rollback.create_history_entry(str(tweak_id))
            self._persist_schema_version(history_id, SCHEMA_VERSION)

            sm = TweakStateMachine(history_id)
            sm.transition("validate")
            sm.transition("apply")

            snapshots = self._run_apply_phase(tweak["actions"]["apply"])
            for snap in snapshots:
                rollback.save_snapshot_v2(history_id, snap)

            v_sem = tweak.get("verify_semantics", "runtime")

            if v_sem == "runtime":
                verify_list = tweak["actions"].get("verify", [])
                if verify_list:
                    ok, _ = self._run_verify_phase(
                        verify_list,
                        is_precheck=False
                    )
                    if not ok:
                        sm.transition(
                            "fail",
                            {"error_message": "Post-apply verification failed"}
                        )
                        raise Exception("Verification failed")

                sm.transition("success")
                sm.transition("verify")

                rollback.mark_applied(history_id)

                print(f"\n[SUCCESS] Tweak '{tweak['name']}' applied and verified.")
                return True

            sm.transition("verify_defer")
            print(f"\n[SUCCESS] Tweak applied. Verification deferred.")
            return True

        except Exception as e:
            print(f"\n[ERROR] {e}")
            print("[INFO] Marking operation as FAILED...")
            try:
                if sm:
                    sm.transition("fail", {"error_message": str(e)})
            except Exception:
                pass
            return False

    def revert(self, tweak_id_str: str) -> bool:
        try:
            tid = TweakID.parse(tweak_id_str)

            conn = sqlite3.connect(rollback.DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, status
                FROM tweak_history
                WHERE tweak_id = ?
                ORDER BY id DESC
                LIMIT 1
            """, (str(tid),))
            row = cursor.fetchone()
            conn.close()

            if not row:
                print(f"[INFO] Tweak '{tid}' not found.")
                return True

            history_id, status = row

            if status == "reverted":
                print(f"[INFO] Tweak '{tid}' already reverted. Hard NOOP.")
                return True

            if status in ("defined", "validated"):
                print(f"[WARN] Cannot revert '{tid}' from state '{status}'.")
                return True

            sm = TweakStateMachine(history_id)
            sm.transition("revert")

            self._rollback_execution(history_id)

            sm.transition("success")
            print(f"\n[SUCCESS] Tweak '{tid}' reverted.")
            return True

        except Exception as e:
            print(f"[ERROR] Revert failed: {e}")
            return True

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
        self,
        verify_actions_list: list,
        is_precheck: bool
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
        return all(results), "Verification complete"

    def _persist_schema_version(self, history_id: int, version: int):
        conn = sqlite3.connect(rollback.DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE tweak_history SET schema_version = ? WHERE id = ?",
            (version, history_id)
        )
        conn.commit()
        conn.close()

    def _execute_rollback_steps(self, history_id: int):
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
        print("  Rollback steps completed successfully.")

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
