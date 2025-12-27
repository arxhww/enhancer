# EnhancerCore – Tweak History State Model

## 1. Scope

This document defines the **formal state machine** governing the lifecycle of a tweak execution within EnhancerCore.

It is authoritative for engine behavior, persistence, recovery, and audit semantics.

The state model is intentionally **closed**. States and transitions are finite, explicit, and irreversible unless stated otherwise.

---

## 2. State Definitions

Each tweak execution produces exactly one history entry, which progresses through one of the states below.

| State         | Description                                                                                        | Terminal |
| ------------- | -------------------------------------------------------------------------------------------------- | -------- |
| `pending`     | History entry created. No side effects have been executed.                                         | No       |
| `applying`    | One or more apply actions are currently executing. System state may be partially modified.         | No       |
| `applied`     | All actions executed successfully and passed verification.                                         | Yes      |
| `rolled_back` | Execution failed during apply or verification. All side effects were reverted.                     | Yes      |
| `reverted`    | Previously applied tweak was manually reverted by the user.                                        | Yes      |
| `recovered`   | History entry was automatically resolved by the recovery subsystem after an interrupted execution. | Yes      |
| `noop`        | Pre-check confirmed the target state was already compliant. No actions were executed.              | Yes      |

Terminal states are final and must never transition to any other state.

---

## 3. Valid State Transitions

Only the following transitions are permitted:

### Normal Execution

* `pending → applying`
* `applying → applied`

### Failure Handling

* `pending → rolled_back`
* `applying → rolled_back`

### Manual User Action

* `applied → reverted`

### Recovery Resolution

* `pending → recovered` (no rollback performed)
* `applying → recovered` (after rollback)

### Pre-check Short-Circuit

* `pending → noop`

Any transition not listed above is invalid by definition and must be rejected by the engine.

---

## 4. Recovery Semantics

The Recovery Manager is executed before any new operation and evaluates **only non-terminal states**.

### Recovery Conditions

1. **State: `pending`**

   * **Interpretation**: History entry created, apply phase never started.
   * **Likely cause**: Process termination before execution began.
   * **Action**: Mark as `recovered`.
   * **Rollback**: NOT performed (no side effects executed).

2. **State: `applying`**

   * **Interpretation**: Execution started but did not complete.
   * **Likely cause**: Crash, forced termination, or system failure during apply.
   * **Action**: Perform rollback using stored snapshots, THEN mark as `recovered`.
   * **Rollback**: REQUIRED (system may have partial modifications).

### Exclusions

The Recovery Manager must **never** modify entries in terminal states:

* `applied`
* `rolled_back`
* `reverted`
* `recovered`
* `noop`

This rule is strict and non-negotiable.

---

## 5. NOOP Semantics

A `noop` entry represents a successful operation with zero side effects.

Characteristics:

* Registered explicitly in history.
* No snapshots are created.
* No rollback is possible or required.
* Treated as terminal and auditable.

This ensures traceability and prevents ambiguity between "not executed" and "not needed".

---

## 6. Persistence Guarantees

The persistence layer enforces the following invariants:

* Every history entry has exactly one final state.
* State transitions are **monotonic** and irreversible.
* No entry may return to `pending` after leaving it.
* Timestamps:

  * **`applied_at`**: Records history entry creation time (NOT completion time).
    * **Note**: The field name is historical and somewhat misleading.
    * It represents when the operation was **initiated**, not when it reached `applied` state.
    * This field is ALWAYS set at entry creation, regardless of final state.
  * **`reverted_at`**: Set only when transitioning to `reverted` state.
    * Records when a previously-applied tweak was manually reverted by user.
* `error_message`: Populated only for:

  * `rolled_back` entries (records apply/verification failure)
  * `recovered` entries (records recovery action taken)

Violations indicate engine bugs, not user error.

---

## 7. Enforcement in Code

State transitions are enforced exclusively through explicit engine methods:

* `create_history_entry()` → Creates entry in `pending` state
* `mark_applying()` → `pending → applying`
* `mark_success()` → `applying → applied`
* `mark_rolled_back()` → `pending/applying → rolled_back`
* `mark_reverted()` → `applied → reverted`
* `mark_noop()` → `pending → noop`
* `_mark_recovered()` → `pending/applying → recovered` (RecoveryManager only)

Direct mutation of the `status` field outside these paths is forbidden.

---

## 8. Design Intent

This state machine prioritizes:

* **Determinism** over flexibility
* **Auditability** over convenience
* **Explicit recovery** over heuristic repair

The model is intentionally conservative.

Any extension must add **new behavior without altering existing state semantics**.

---

## 9. Database Schema Notes

### Field Name Clarifications

The `tweak_history` table contains a field named `applied_at` which, despite its name, actually records the **creation timestamp** of the history entry.

**Why not rename it?**

* Breaking change for existing databases
* Would require migration logic
* Field serves its purpose despite naming ambiguity

**Semantic Truth**:

* `applied_at` = history entry creation time
* NOT the timestamp of transition to `applied` state
* Set once at entry creation, never modified

This is explicitly documented here to prevent future confusion.

If creating a new version of the schema (v2+), consider renaming to `created_at` for clarity.