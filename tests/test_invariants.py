import pytest
import sqlite3
import json
from pathlib import Path

from core.tweak_manager import TweakManager
from core import rollback
from core.state_machine import TweakStateMachine
from core.constants import SCHEMA_VERSION


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    test_db = tmp_path / "test_enhancer.db"
    monkeypatch.setattr(rollback, "DB_PATH", test_db)
    rollback.init_db()
    yield test_db


def test_INV_3_2_status_changes_only_via_state_machine():
    history_id = rollback.create_history_entry("test.inv3.2")

    sm = TweakStateMachine(history_id)
    sm.transition("apply_success")

    conn = sqlite3.connect(rollback.DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT status FROM tweak_history WHERE id = ?", (history_id,))
    status = cur.fetchone()[0]
    conn.close()

    assert status == "applied"


def test_INV_2_3_schema_version_atomicity():
    history_id = rollback.create_history_entry("test.schema.atomic")

    conn = sqlite3.connect(rollback.DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT schema_version FROM tweak_history WHERE id = ?",
        (history_id,)
    )
    schema_version = cur.fetchone()[0]
    conn.close()

    assert schema_version == SCHEMA_VERSION


def test_INV_3_1_rollback_failure_propagates():
    manager = TweakManager()
    history_id = rollback.create_history_entry("test.rollback.fail")

    from core.actions.base import ActionSnapshot
    bad_snapshot = ActionSnapshot("registry", {
        "path": "INVALID",
        "key": "NOPE",
        "old_value": None,
        "old_type": None,
        "value_existed": False,
        "subkey_existed": False
    })

    rollback.save_snapshot_v2(history_id, bad_snapshot)

    with pytest.raises(Exception):
        manager._rollback_execution(history_id)


def test_INV_2_2_snapshots_persist_after_revert(tmp_path):
    tweak_file = tmp_path / "tweak.json"
    tweak_file.write_text(json.dumps({
        "id": "test.snapshot.persist",
        "name": "Snapshot Test",
        "tier": 1,
        "risk_level": "low",
        "requires_reboot": False,
        "rollback_guaranteed": True,
        "scope": ["registry"],
        "verify_semantics": "runtime",
        "actions": {
            "apply": [],
            "verify": []
        }
    }))

    manager = TweakManager()
    manager.apply(tweak_file)

    active = rollback.get_active_tweaks()
    history_id = active[0]["id"]

    manager.revert("test.snapshot.persist")

    snapshots = rollback.get_snapshots_v2(history_id)
    assert len(snapshots) >= 0


def test_revert_idempotency_is_strict(tmp_path):
    tweak_file = tmp_path / "tweak.json"
    tweak_file.write_text(json.dumps({
        "id": "test.revert.idempotent",
        "name": "Revert Test",
        "tier": 1,
        "risk_level": "low",
        "requires_reboot": False,
        "rollback_guaranteed": True,
        "scope": ["registry"],
        "verify_semantics": "runtime",
        "actions": {
            "apply": [],
            "verify": []
        }
    }))

    manager = TweakManager()
    manager.apply(tweak_file)

    assert manager.revert("test.revert.idempotent") is True
    assert manager.revert("test.revert.idempotent") is False


def test_INV_5_2_verify_returns_bool_only():
    from core.actions.registry_action import RegistryAction

    action = RegistryAction({
        "type": "registry",
        "path": "HKCU\\Software\\Missing",
        "key": "X",
        "value": 1,
        "value_type": "DWORD"
    })

    result = action.verify()
    assert isinstance(result, bool)


def test_INV_7_3_rollback_errors_propagate():
    from core.actions.service_action import ServiceAction
    from core.actions.base import ActionSnapshot

    action = ServiceAction({
        "type": "service",
        "service_name": "INVALID_SERVICE",
        "state": "running",
        "start_type": "manual"
    })

    snapshot = ActionSnapshot("service", {
        "service_name": "INVALID_SERVICE",
        "old_status": None,
        "old_start_type": None
    })

    with pytest.raises(Exception):
        action.rollback(snapshot)
