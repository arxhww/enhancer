from . import rollback
from .tweak_state import TweakState


def assert_no_applied_without_snapshots(history_id: int):
    snaps = rollback.get_snapshots_v2(history_id)
    if not snaps:
        raise AssertionError(
            f"Invariant violated: applied tweak {history_id} has no snapshots"
        )


def assert_reverted_keeps_snapshots(history_id: int):
    snaps = rollback.get_snapshots_v2(history_id)
    if snaps is None:
        raise AssertionError(
            f"Invariant violated: reverted tweak {history_id} lost snapshots"
        )


def assert_verify_is_read_only(before_row: dict, after_row: dict):
    if before_row["status"] != after_row["status"]:
        raise AssertionError("Invariant violated: verify mutated state")


def assert_recover_does_not_create_history(before_ids: set, after_ids: set):
    if before_ids != after_ids:
        raise AssertionError("Invariant violated: recover created history entries")
