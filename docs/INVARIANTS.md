# EnhancerCore – Engine Invariants

## 1. Purpose

This document defines the **absolute guarantees**, **hard constraints**, and **forbidden behaviors**
of the EnhancerCore execution engine.

Anything not explicitly allowed is **forbidden by default**.

These invariants exist to:
- Prevent undefined behavior
- Eliminate silent corruption
- Make failure modes explicit
- Freeze the semantic contract of the engine

This document is normative. Tests enforce it. Code must obey it.

---

## 2. Persistence & History Invariants

### 2.1 History Entry Lifecycle

- A history entry is created **before** any execution occurs.
- Each entry has exactly one immutable `tweak_id`.
- History entries are append-only except for:
  - `status`
  - `applied_at`
  - `reverted_at`
  - `verified_at`

### 2.2 Terminal State Immutability

Once a history entry reaches a terminal state, it **must never transition again**.

Terminal states:
- `applied`
- `verified`
- `reverted`
- `recovered`
- `noop`

Rules:
- Terminal states are write-once.
- Any attempt to mutate a terminal entry is a logic error.
- Administrative repair is explicitly out of scope.

### 2.3 Snapshot Persistence

- Snapshots are **never deleted automatically** by revert.
- Revert restores state but preserves historical evidence.
- Snapshots are retained for:
  - Recovery
  - Audit
  - Deterministic re-execution

Deletion is allowed **only** via explicit retention or pruning policies.

---

## 3. Snapshot Invariants

### 3.1 Creation Order

- A snapshot is created **before** any `apply()` side effect.
- If snapshot creation fails, execution must not proceed.
- Snapshot creation is mandatory for all rollback-guaranteed tweaks.

### 3.2 Restoration Rules

- Rollback restores **only** data explicitly captured in the snapshot.
- No inference, guessing, or reconstruction is permitted.
- Rollback must be deterministic and idempotent.

### 3.3 Idempotency

- Rolling back the same snapshot multiple times is safe.
- Reverting an already reverted tweak is a no-op.
- Revert never fails due to missing side effects.

---

## 4. Schema & Versioning Invariants

### 4.1 Schema Authority

- `SCHEMA_VERSION` is the single authoritative engine schema.
- A tweak declaring a mismatched `schema_version` is rejected **before execution**.
- Validation failure aborts the entire operation.

### 4.2 Freeze Rule

- `SCHEMA_VERSION` changes only via explicit version releases.
- Hot patches that alter schema semantics are forbidden.
- Migration logic must be explicit, reversible, and test-covered.

---

## 5. Execution Flow Invariants

### 5.1 Batch Atomicity

- A batch executes as a single logical transaction.
- Any failure triggers rollback of **all** executed actions.
- Partial success is forbidden.
- No side effects may survive a failed batch.

### 5.2 Action Atomicity

- Each action must be:
  - Fully successful, or
  - Clearly failed
- Partial application inside an action is forbidden.
- Action code must not manage its own compensation logic.

### 5.3 Centralized Rollback Control

- Only the top-level engine may initiate rollback.
- Actions must never trigger rollback directly.
- Rollback order is strictly reverse-application order.

---

## 6. State Machine Invariants

### 6.1 Single Authority

- `TweakStateMachine` is the **only** component allowed to mutate `tweak_history.status`.
- Direct database writes outside the state machine are forbidden.

### 6.2 Strict Transition Graph

- All state transitions must follow the declared transition graph.
- Illegal transitions are logic errors and must raise immediately.
- No implicit or derived states are allowed.

---

## 7. Crash & Recovery Invariants

### 7.1 Crash Safety

- A crash during apply must leave the system in:
  - `reverted`, or
  - a recoverable intermediate state
- No zombie “applied” entries without snapshots may exist.

### 7.2 Recovery Semantics

- Recovery:
  - Detects incomplete executions
  - Replays rollback using persisted snapshots
- Recovery is idempotent.
- Recovery never applies new side effects.

---

## 8. Validation Invariants

### 8.1 Validation Order

1. Batch-level composition rules
2. Schema validation
3. Dependency validation
4. Conflict validation

Structural invalidity always aborts before execution.

### 8.2 Schema Contract

- `TWEAK_SCHEMA.md` defines the contract.
- `TweakValidator` enforces it.
- Any divergence between schema and code is a code bug.

---

## 9. Composition Invariants

### 9.1 Batch Purity

A batch must be homogeneous with respect to:
- Tier
- Verify semantics
- Reboot requirement
- Boot scope

Violation aborts execution before any action runs.

### 9.2 Dependency Rules

- Dependencies are validated before execution.
- Dependencies are **never auto-applied**.
- Circular dependencies invalidate the batch.

### 9.3 Conflict Rules

- Conflicts with active tweaks invalidate execution.
- Intra-batch conflicts are forbidden.
- Conflict detection is fail-fast.

---

## 10. API Invariants

### 10.1 Public Interfaces

- Public methods return only primitive or standard types.
- Exceptions exposed:
  - `ValidationError` (contract violation)
  - `RuntimeError` (engine failure)
- Internal exceptions must not leak.

### 10.2 Configuration Handling

- Loaded tweak definitions are immutable.
- Validators operate on deep copies.
- No runtime mutation of tweak definitions is allowed.

---

## 11. Negative Constraints

The engine will **never**:

1. Automatically reboot the system.
2. Automatically resolve or apply dependencies.
3. Suppress errors to report success.
4. Write success states if verification fails.
5. Guess previous system state during rollback.
6. Apply tweaks implicitly.
7. Mutate terminal history entries.
8. Execute Tier 3 tweaks in batches.
9. Delete snapshots on revert.
10. Recover by re-applying actions.

---

## 12. Versioning

- **v2.0.0**: Formal invariant freeze aligned with engine v2 architecture.
- Any modification to this document requires a version bump.
- Breaking invariant changes require a major version increment.
