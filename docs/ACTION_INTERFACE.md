# EnhancerCore – Action Interface Contract

## 1. Purpose

This document defines the **mandatory interface** that all action types must implement to participate in EnhancerCore's transactional lifecycle.

This is a **contract**, not implementation guidance. Any action type violating this contract is invalid by definition.

---

## 2. Scope

An **Action** is the atomic unit of system modification in EnhancerCore.

Actions are:
- The only mechanism through which the engine modifies system state
- Responsible for their own snapshot, apply, verify, and rollback logic
- Type-specific (registry, service, power, boot, etc.)
- Independently testable and composable

Actions are NOT:
- Tweaks (tweaks contain actions)
- Metadata (metadata describes tweaks, not actions)
- State transitions (state machine is separate)

---

## 3. Mandatory Methods

Every action type MUST implement exactly these five methods.

### 3.1 `snapshot() → ActionSnapshot`

**Purpose**: Capture current system state before modification.

**Contract**:
- MUST be idempotent (calling twice produces identical snapshots)
- MUST be read-only (no side effects)
- MUST capture ALL information needed for complete rollback
- MUST succeed or throw exception (no partial snapshots)

**Timing**: Called once before `apply()`, results stored in database.

**Returns**: `ActionSnapshot` containing:
- `action_type`: String matching action type identifier
- `metadata`: Dictionary with all state needed for rollback

**Throws**: If snapshot operation fails (permissions, system state, etc.).

**Example Semantics**:
```
For RegistryAction:
  - Capture: key existence, value, type, subkey existence
  
For ServiceAction:
  - Capture: startup type, current state, service existence
```

---

### 3.2 `apply() → None`

**Purpose**: Execute the system modification.

**Contract**:
- MUST be atomic where possible
- MUST throw on any failure (triggers rollback)
- MUST NOT return partial success
- MAY have immediate side effects

**Timing**: Called after `snapshot()`, before `verify()`.

**Returns**: Nothing (success indicated by not throwing).

**Throws**: If modification fails for any reason.

**Critical Rule**: If `apply()` throws, engine immediately calls `rollback()` on all previously-applied actions in reverse order.

**Example Semantics**:
```
For RegistryAction:
  - Write registry key/value
  - Create subkey if needed (based on force_create flag)
  
For ServiceAction:
  - Modify service startup type
  - Start/stop service if requested
```

---

### 3.3 `verify() → bool`

**Purpose**: Confirm system state matches expectations after `apply()`.

**Contract**:
- MUST be deterministic (same state → same result)
- MUST check both value AND type (where applicable)
- MUST NOT have side effects
- MUST respect `verify_semantics` from tweak metadata

**Timing**: Called immediately after `apply()`.

**Returns**: 
- `True`: System state matches expectations
- `False`: Verification failed (triggers rollback)

**Does NOT Throw**: Returns `False` instead of throwing.

**Critical Rule**: If `verify()` returns `False`, engine treats this as apply failure and triggers rollback.

**Example Semantics**:
```
For RegistryAction:
  - Read back registry value
  - Confirm value matches expected
  - Confirm type matches expected
  
For ServiceAction:
  - Query service configuration
  - Confirm startup type matches expected
  - Confirm state matches expected (if specified)
```

---

### 3.4 `rollback(snapshot: ActionSnapshot) → None`

**Purpose**: Restore system to state captured in snapshot.

**Contract**:
- MUST use ONLY information from snapshot (no external state)
- MUST be as atomic as possible
- MUST succeed even if `apply()` was only partially completed
- SHOULD use `force` mode to ensure restoration succeeds

**Timing**: Called in reverse order when:
- Any action's `apply()` throws
- Any action's `verify()` returns `False`
- Recovery manager detects interrupted operation

**Returns**: Nothing (success indicated by not throwing).

**Throws**: If rollback is impossible (critical error, requires manual intervention).

**Critical Rule**: Rollback failure is a **severe error**. System state is undefined.

**Example Semantics**:
```
For RegistryAction:
  - If value existed: restore old value/type
  - If value didn't exist: delete value
  - If subkey didn't exist: delete subkey (if empty)
  
For ServiceAction:
  - Restore previous startup type
  - Restore previous state (running/stopped)
```

---

### 3.5 `from_snapshot(snapshot: ActionSnapshot) → Action`

**Purpose**: Reconstruct action instance from snapshot for rollback.

**Contract**:
- MUST be a class method (not instance method)
- MUST validate snapshot `action_type` matches expected type
- MUST reconstruct action capable of performing rollback
- MUST NOT require original tweak definition

**Timing**: Called during rollback to deserialize actions from database.

**Returns**: Action instance ready to call `rollback()`.

**Throws**: If snapshot is invalid or incompatible.

**Rationale**: Ensures rollback doesn't depend on fragile metadata rehidration. Each action type knows how to rebuild itself from its own snapshot format.

**Example Semantics**:
```
For RegistryAction:
  - Extract path, key, old_value, old_type from snapshot.metadata
  - Construct minimal definition for rollback
  - Store snapshot metadata for use in rollback()
```

---

## 4. Optional Method

### 4.1 `get_description() → str`

**Purpose**: Human-readable description for logging.

**Contract**:
- SHOULD be concise (one line)
- SHOULD describe what the action does, not how
- Used in console output and logs

**Default Implementation**: Returns `"{action_type} action"`.

**Example**:
```
"Set HKLM\Software\Test\Value = 1"
"Service 'SysMain' startup=disabled state=stopped"
```

---

## 5. Action Types

### 5.1 Current Action Types

| Type | Identifier | Scope |
|------|------------|-------|
| Registry | `"registry"` | Windows Registry modifications |
| Service | `"service"` | Windows service configuration |

### 5.2 Future Action Types

Planned but not yet implemented:

| Type | Identifier | Scope |
|------|------------|-------|
| PowerConfig | `"powercfg"` | Power management settings |
| BootConfig | `"bcdedit"` | Boot configuration |
| ScheduledTask | `"scheduled_task"` | Task Scheduler |
| Filesystem | `"filesystem"` | File permissions/attributes |

---

## 6. ActionSnapshot Structure

### 6.1 Required Fields

```python
class ActionSnapshot:
    action_type: str  # Matches action type identifier
    metadata: dict    # Type-specific rollback data
```

### 6.2 Serialization Contract

**To Database**:
```python
{
  "action_type": "registry",
  "metadata": {
    "path": "HKLM\\Software\\Test",
    "key": "Value",
    "old_value": 0,
    "old_type": 4,  # REG_DWORD
    "value_existed": True,
    "subkey_existed": True
  }
}
```

**From Database**:
```python
ActionSnapshot.from_dict(db_row)
```

### 6.3 Metadata Contract

Metadata dictionary MUST contain:
- All information needed for `rollback()`
- NO information needed for `apply()` or `verify()`
- Type-specific fields (registry needs paths, service needs names)

Metadata MUST NOT contain:
- Circular references
- Non-serializable types
- External resource handles

---

## 7. Verification Actions

### 7.1 Special Case: Read-Only Actions

Verification actions (used in tweak `verify` phase) have modified contract:

**Must Implement**:
- `verify() → bool` (core functionality)
- `get_description() → str`

**Must Raise NotImplementedError**:
- `snapshot()` - Verify actions don't participate in rollback
- `apply()` - Verify actions are read-only
- `rollback()` - Verify actions don't modify state
- `from_snapshot()` - Verify actions aren't deserialized

**Rationale**: Verification actions are read-only checks, not modifications.

---

## 8. Error Handling

### 8.1 Snapshot Failures

If `snapshot()` throws:
- Operation aborts immediately
- No `apply()` is called
- No rollback needed (no changes made)
- History entry marked as `rolled_back` with error

### 8.2 Apply Failures

If `apply()` throws:
- All previously-applied actions rolled back in reverse order
- Current action's `rollback()` NOT called (nothing to undo)
- History entry marked as `rolled_back` with error

### 8.3 Verify Failures

If `verify()` returns `False`:
- Treated as apply failure
- All actions rolled back in reverse order
- History entry marked as `rolled_back` with "Verification failed"

### 8.4 Rollback Failures

If `rollback()` throws:
- **Critical error** - system state undefined
- History entry marked as `rolled_back` with both errors
- User notified of manual intervention requirement
- NO automatic retry

---

## 9. Action Registration

### 9.1 Registry Location

Actions register in `ACTION_REGISTRY` dictionary:

```python
ACTION_REGISTRY = {
    "registry": RegistryAction,
    "service": ServiceAction,
    # Future types here
}
```

### 9.2 Registration Requirements

To register a new action type:
1. Implement all five mandatory methods
2. Add to `ACTION_REGISTRY` in `core/actions/factory.py`
3. Create corresponding verify action (if applicable)
4. Update this document with type definition
5. Add to manifest for integrity checking

---

## 10. Lifecycle Guarantees

### 10.1 Execution Order

For a single action:
1. `snapshot()` - once
2. `apply()` - once
3. `verify()` - once
4. If failure: `rollback(snapshot)` - once

### 10.2 Idempotency

**Required**:
- `snapshot()` is idempotent
- `verify()` is idempotent

**Not Required**:
- `apply()` may have side effects
- `rollback()` may have side effects

### 10.3 Atomicity

**Per-Action**: Best effort atomicity (use system primitives).

**Per-Batch**: All-or-nothing via rollback mechanism.

---

## 11. Testing Contract

Every action type MUST be testable with:

1. **Snapshot Test**: Verify snapshot captures complete state
2. **Apply Test**: Verify modification succeeds
3. **Verify Test**: Verify detection of correct/incorrect state
4. **Rollback Test**: Verify restoration to original state
5. **Idempotency Test**: Verify snapshot/verify can run multiple times

---

## 12. Violation Consequences

Violating this contract causes:

| Violation | Consequence |
|-----------|-------------|
| `snapshot()` not idempotent | Rollback may use wrong state |
| `apply()` partial success | Undefined system state |
| `verify()` has side effects | State corruption |
| `rollback()` uses external state | Cannot restore after process restart |
| Missing `from_snapshot()` | Recovery system fails |

All violations are **bugs**, not user errors.

---

## 13. Version

This document is **version 1.0**.

Changes to method signatures or contracts require version increment and migration path for existing action types.

---

## 14. Non-Goals

This document does NOT define:
- Tweak metadata schema (see TWEAK_SCHEMA.md)
- Composition rules (see TWEAK_RULES.md)
- State machine (see STATES.md)
- Implementation details (see source code)

This is **interface contract only**. Implementation is separate.