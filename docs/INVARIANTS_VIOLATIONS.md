# Known Invariant Violations

**Generated**: Post-v1.2.0 commit  
**Status**: Enumeration only (no corrections applied)

---

## [INV-3.2] Single Authority over status

**File**: `core/rollback.py`  
**Lines**: 91-97, 103-110, 174-180  
**Issue**: Direct SQL writes to `tweak_history.status` bypass `TweakStateMachine`  
**Impact**: State machine authority violated, state transitions not enforced  
**Evidence**:
```python
# Line 91-97: mark_reverted()
cursor.execute("""
    UPDATE tweak_history
    SET status = 'reverted', ...
""")

# Line 103-110: mark_applied()
cursor.execute("""
    UPDATE tweak_history
    SET status = 'applied'
""")
```

**Contract Violation**: INVARIANTS.md § 3.2 "Only `TweakStateMachine` may mutate `tweak_history.status`"

---

## [INV-2.3] Schema Versioning Authority

**File**: `core/tweak_manager.py`  
**Lines**: 144-155 (`_persist_schema_version`)  
**Issue**: Schema version persistence is manual and decoupled from history creation  
**Impact**: Race condition possible between history creation and version write  
**Evidence**:
```python
def _persist_schema_version(self, history_id: int, version: int):
    # Separate transaction after history entry exists
    cursor.execute(
        "UPDATE tweak_history SET schema_version = ? WHERE id = ?",
        (version, history_id)
    )
```

**Contract Violation**: INVARIANTS.md § 2.3 "`SCHEMA_VERSION` is the single source of truth"  
**Expected**: Schema version set atomically with history entry creation

---

## [INV-3.1] Batch Atomicity - Partial Rollback

**File**: `core/tweak_manager.py`  
**Lines**: 86-92  
**Issue**: Exception during rollback prints success message but may leave partial state  
**Impact**: Rollback failure doesn't propagate cleanly, violates all-or-nothing guarantee  
**Evidence**:
```python
try:
    if sm:
        self._rollback_execution(sm.history_id)
        sm.transition("fail", {"error_message": str(e)})
except Exception as rb_err:
    print(f"[CRITICAL] Rollback Failed: {rb_err}")
    # Status still set to "fail" even if rollback incomplete
```

**Contract Violation**: INVARIANTS.md § 3.1 "Partial success is forbidden"  
**Expected**: Rollback failure should leave status as undefined/corrupted, not "fail"

---

## [INV-3.3] Centralized Rollback Control

**File**: `core/recovery.py`  
**Lines**: 60-72  
**Issue**: Recovery manager directly calls `manager._rollback_execution()` outside normal flow  
**Impact**: Rollback triggered from multiple entry points, not centralized  
**Evidence**:
```python
# Recovery calls rollback directly
manager._rollback_execution(issue["history_id"])
```

**Partial Violation**: INVARIANTS.md § 3.3 "Rollback is initiated only by the top-level executor"  
**Context**: Recovery is an exception but should be documented as authorized caller

---

## [INV-2.2] Snapshots - Deletion Policy

**File**: `core/tweak_manager.py`  
**Lines**: 167-171 (in `revert()`)  
**Issue**: Snapshots deleted immediately after revert, violating retention policy  
**Impact**: Cannot re-apply or audit reverted tweaks  
**Evidence**:
```python
rollback.mark_reverted(history_id)
self._rollback_execution(history_id)
rollback.clear_snapshots(history_id)  # Immediate deletion
```

**Contract Violation**: INVARIANTS.md § 2.2 "Snapshots are deleted only through explicit retention or pruning policies"  
**Expected**: Snapshots should persist until explicit cleanup operation

---

## [INV-5.2] Schema-Code Divergence

**File**: `core/actions/registry_action.py`  
**Lines**: 44-45  
**Issue**: `verify()` returns `Tuple[bool, str]` but ACTION_INTERFACE.md specifies `bool`  
**Impact**: Interface contract violation, non-standard return type  
**Evidence**:
```python
def verify(self) -> Tuple[bool, str]:
    # ...
    return False, "value missing"
```

**Contract Violation**: ACTION_INTERFACE.md § 3.3 "Returns: True/False only"  
**Expected**: Return `bool` only, use exceptions or logging for diagnostics

---

## [INV-7.3] Suppressing Errors

**File**: `core/actions/service_action.py`  
**Lines**: 68-71, 73-76  
**Issue**: Rollback silently suppresses exceptions during service state restoration  
**Impact**: Rollback failures hidden, violates "never suppress errors" rule  
**Evidence**:
```python
try:
    win32service.StartService(meta["service_name"])
except Exception:
    pass  # Silent suppression
```

**Contract Violation**: INVARIANTS.md § 7.3 "Suppress errors to report success"  
**Expected**: Rollback exceptions should propagate or be logged as critical

---

## [INV-7.5] Guessing Previous State

**File**: `core/actions/powercfg_action.py`  
**Lines**: 84-91  
**Issue**: Rollback assumes both AC and DC must be restored without checking snapshot completeness  
**Impact**: May set incorrect values if snapshot was partial  
**Evidence**:
```python
def rollback(self, snapshot: ActionSnapshot) -> None:
    # Always sets both AC and DC from snapshot
    # No validation that these fields existed in original apply
    self._exec_powercfg(["/setacvalueindex", ...])
    self._exec_powercfg(["/setdcvalueindex", ...])
```

**Minor Violation**: INVARIANTS.md § 7.5 "Never guess previous system state"  
**Context**: Should verify which values were actually captured in snapshot

---

## [INV-6.1] Return Types - Internal Exception Leakage

**File**: `core/actions/bcdedit_action.py`  
**Lines**: 26-30  
**Issue**: `RuntimeError` with raw subprocess output may leak internal details  
**Impact**: Internal implementation details exposed through exception messages  
**Evidence**:
```python
if result.returncode != 0:
    raise RuntimeError(
        f"bcdedit failed with code {result.returncode}: {result.stderr}"
    )
```

**Minor Violation**: INVARIANTS.md § 6.1 "Internal exceptions must not leak"  
**Expected**: Wrap in `ValidationError` or sanitize message

---

## [INV-4.3] Conflicts - Fail Fast

**File**: `core/tweak_manager.py`  
**Lines**: 30-33  
**Issue**: Conflict detection happens after tweak load, not during composition validation  
**Impact**: Validation not at composition time as specified in TWEAK_RULES.md  
**Evidence**:
```python
# Inside apply(), after load
active_ids = [t['tweak_id'] for t in rollback.get_active_tweaks()]
self.validator.validate_composition([tweak], active_ids)
```

**Contract Violation**: TWEAK_RULES.md § 4.3 "Conflicts abort execution before any action runs"  
**Expected**: Conflict detection should be separate method called before apply

---

## [INV-2.1] State Immutability - Verified Timestamp

**File**: `core/rollback.py`  
**Lines**: Schema definition  
**Issue**: `verified_at` field suggests post-hoc verification updates to terminal states  
**Impact**: Terminal state may be modified after reaching `applied`  
**Evidence**:
```python
# Schema allows verified_at to be set after applied
CREATE TABLE IF NOT EXISTS tweak_history (
    ...
    verified_at TIMESTAMP,
    ...
)
```

**Potential Violation**: INVARIANTS.md § 2.1 "Terminal states are write-once"  
**Context**: If `verified_at` is set after status='applied', this violates immutability