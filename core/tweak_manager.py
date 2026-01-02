import json
from pathlib import Path
from typing import List, Tuple, Optional, Any, Dict

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
from infra.telemetry.writer import emit
from .invariants import assert_no_applied_without_snapshots

def _hook(event: str, ctx: dict) -> None:
    emit({
        "event": event,
        "tweak_id": ctx.get("tweak_id"),
        "history_id": ctx.get("history_id"),
        "result": ctx.get("result"),
        "error": str(ctx.get("error")) if ctx.get("error") else None
    })

class TweakManager:

    def __init__(self):
        self.validator = TweakValidator()
        self._rollback_execution = self._execute_rollback_steps
        try:
            migrate_to_v2()
        except Exception as e:
            print(f"[WARN] Database migration issue: {e}")

    def load_tweak(self, tweak_path: Path) -> dict:
        with open(tweak_path, "r", encoding="utf-8") as f:
            tweak_def = json.load(f)
        self.validator.validate_definition(tweak_def)
        return tweak_def

    def apply(self, tweak_path: Path) -> bool:
        tweak_path = tweak_path.resolve()

        sm: Optional[TweakStateMachine] = None

        ctx: Dict[str, Any] = {
            "command": "apply",
            "tweak_path": str(tweak_path),
        }

        try:
            tweak = self.load_tweak(tweak_path)
            tweak_id = TweakID.parse(tweak["id"])
            ctx["tweak_id"] = str(tweak_id)

            existing = rollback.get_history_by_tweak_id(str(tweak_id))

            if existing:
                history_id = existing["id"]
                sm = TweakStateMachine(history_id)
                state = sm.get_current_state()
                ctx["history_id"] = history_id

                if state == TweakState.VERIFIED:
                    ctx["result"] = "noop"
                    return True

                if state != TweakState.REVERTED:
                    raise RuntimeError(f"Cannot apply tweak in state {state}")

            else:
                history_id = rollback.create_history_entry(str(tweak_id))
                self._persist_schema_version(history_id, SCHEMA_VERSION)
                sm = TweakStateMachine(history_id)
                sm.transition("validate")

            sm.transition("apply")

            snapshots = self._run_apply_phase(tweak["actions"].get("apply", []))
            for snap in snapshots:
                rollback.save_snapshot_v2(history_id, snap)

            verify_list = tweak["actions"].get("verify", [])
            if verify_list:
                ok, _ = self._run_verify_phase(verify_list, is_precheck=False)
                if not ok:
                    raise RuntimeError("Post-apply verification failed")

            sm.transition("success")
            sm.transition("verify")

            rollback.mark_applied(history_id)

            ctx["result"] = "success"
            return True


        except Exception as e:
            if history_id is not None:
                try:
                    self._rollback_execution(history_id)
                    rollback.mark_reverted(history_id)
                except Exception:
                    pass

            ctx["result"] = "failure"
            ctx["error"] = e
            return False

        finally:
            _hook("apply", dict(ctx))

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
        return Executor().run_steps(steps)

    def _run_verify_phase(
        self, verify_actions_list: list, is_precheck: bool
    ) -> Tuple[bool, str]:

        class VerifyStep:
            def __init__(self, action):
                self.action = action

            def execute(self):
                return self.action.verify()

        steps = [VerifyStep(create_verify_action(v)) for v in verify_actions_list]
        results = Executor().run_steps(steps)
        return all(results), "ok"

    def _persist_schema_version(self, history_id: int, version: int):
        import sqlite3

        conn = sqlite3.connect(rollback.DB_PATH)
        try:
            conn.execute(
                "UPDATE tweak_history SET schema_version = ? WHERE id = ?",
                (version, history_id),
            )
            conn.commit()
        finally:
            conn.close()

    def _execute_rollback_steps(self, history_id: int):
        raw_snapshots = rollback.get_snapshots_v2(history_id)
        if not raw_snapshots:
            return

        class RollbackStep:
            def __init__(self, action, snapshot):
                self.action = action
                self.snapshot = snapshot

            def execute(self):
                self.action.rollback(self.snapshot)

        steps = []
        for snap_dict in reversed(raw_snapshots):
            snap = ActionSnapshot.from_dict(snap_dict)
            action = create_action_from_snapshot(snap)
            steps.append(RollbackStep(action, snap))

        Executor().run_steps(steps)

    def revert(self, tweak_id_str: str) -> bool:
        ctx = {"command": "revert", "tweak_id": tweak_id_str}

        row = rollback.get_history_by_tweak_id(tweak_id_str)
        if not row:
            ctx["result"] = "noop"
            _hook("revert", dict(ctx))
            return True

        history_id = row["id"]

        try:
            self._rollback_execution(history_id)
        except Exception:
            pass

        rollback.mark_reverted(history_id)

        ctx["result"] = "success"
        _hook("revert", dict(ctx))
        return True

    def list_active(self) -> None:
        tweaks = rollback.get_active_tweaks()
        if not tweaks:
            print("\nNo active tweaks found.")
            return

        print("\n[ACTIVE TWEAKS]")
        for t in tweaks:
            print(
                f"  • {t['tweak_id']} "
                f"(Status: {t.get('status', 'unknown')}, "
                f"Applied: {t['applied_at']})"
            )
            
    def verify(self, tweak_id_str: str) -> bool:
        row = rollback.get_history_by_tweak_id(tweak_id_str)
        if not row:
            return True

        verify_actions = rollback.get_verify_actions(row["id"])
        if not verify_actions:
            return True

        ok, _ = self._run_verify_phase(verify_actions, is_precheck=True)
        return ok
    
    def recover(self, *_args, **_kwargs) -> bool:
        from infra.recovery.manager import RecoveryManager

        rm = RecoveryManager()
        rm.recover(self)
        return True
    
    def dry_run(self, tweak_path: Path) -> bool:
        tweak = self.load_tweak(tweak_path)
        actions = tweak["actions"].get("apply", [])

        class DryRunStep:
            def __init__(self, action):
                self.action = action

            def execute(self):
                self.action.snapshot()
                return True

        steps = [DryRunStep(create_action(a)) for a in actions]
        Executor().run_steps(steps)
        return True
    
    def reexplain(self, tweak_path: Path) -> None:
        tweak = self.load_tweak(tweak_path)

        explanation = {
            "id": tweak["id"],
            "tier": tweak["tier"],
            "risk_level": tweak["risk_level"],
            "rollback_guaranteed": tweak["rollback_guaranteed"],
            "requires_reboot": tweak["requires_reboot"],
            "scope": tweak["scope"],
            "verify_semantics": tweak["verify_semantics"],
            "apply_actions": len(tweak["actions"].get("apply", [])),
            "verify_actions": len(tweak["actions"].get("verify", [])),
        }

        print(json.dumps(explanation, indent=2))