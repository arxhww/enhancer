```markdown
# EnhancerCore – Engine Invariants

## 1. Purpose

This document defines the **absolute guarantees** and **negative constraints** of the EnhancerCore engine.

If a behavior is not explicitly listed as allowed, it is **forbidden by default**.

These invariants exist to eliminate undefined behavior, silent corruption, and semantic ambiguity.

---

## 2. Data Persistence Invariants

### 2.1 State Immutability
- **History Entries**: Once a history entry reaches a terminal state (`applied`, `rolled_back`, `reverted`, `recovered`, `noop`), its `status` field **never changes**.
- Terminal states are write-once.
- Any modification outside engine code is considered administrative repair and out of scope.

### 2.2 Snapshots
- **Creation**: Snapshots are created **before** any `apply()` action is executed.
- **Restoration**: Rollback restores **only** the data captured in the snapshot.
- **No Inference**: The engine never infers or reconstructs prior state.
- **Deletion**: Snapshots are deleted only through explicit retention or pruning policies.

### 2.3 Schema Versioning
- **Authority**: `SCHEMA_VERSION` is the single source of truth.
- **Validation**: Any tweak declaring a different `schema_version` is rejected before execution.
- **Freeze Rule**: `SCHEMA_VERSION` is incremented only via explicit version release. No hot patches.

---

## 3. Execution Flow Invariants

### 3.1 Atomicity
- **Batch Atomicity**: A batch executes as a single logical transaction.
  - Any failure triggers rollback of all applied actions in the batch.
  - Partial success is forbidden.
- **Action Atomicity**: Each action must be atomic or fail clearly.
  - Actions must not return partial success states.

### 3.2 State Transitions
- **Strict Graph**: All transitions must follow the `TweakState` transition graph.
- **Single Authority**: Only `TweakStateMachine` may mutate `tweak_history.status`.
- **No Implicit States**: No hidden or inferred states exist outside the enum.

### 3.3 Error Handling
- **Rollback Triggers**:
  1. Exception during `apply()`
  2. `verify()` returns `False`
  3. Explicit recovery logic
- **Centralized Control**: Rollback is initiated only by the top-level executor.
- **Action Code Limitation**: Action implementations never trigger rollback directly.

---

## 4. Composition Invariants

### 4.1 Batching Rules
- **Tier Purity**: A batch contains tweaks of exactly one tier.
- **Verify Semantics Purity**: A batch contains exactly one `verify_semantics` type.
- **Reboot Purity**: Tweaks requiring reboot cannot batch with non-reboot tweaks.
- **Boot Isolation**: Tweaks with `boot` scope cannot batch with non-boot tweaks.

### 4.2 Dependencies
- **Pre-Apply Validation**: Dependencies are checked before execution.
- **No Auto-Resolution**: The engine never applies or installs dependencies automatically.
- **Circular Dependency Ban**: Circular dependencies invalidate the batch.

### 4.3 Conflicts
- **Active Conflict Check**: Conflicts with active tweaks invalidate the batch.
- **Intra-Batch Conflicts**: Conflicting tweaks cannot coexist in the same batch.
- **Fail Fast**: Conflicts abort execution before any action runs.

---

## 5. Validation Invariants

### 5.1 Order of Validation
- **Composition First**: Batch-level rules are evaluated before individual tweak rules.
- **Rationale**: Structural invalidity takes precedence over configuration errors.

### 5.2 Schema Authority
- **Specification**: `TWEAK_SCHEMA.md` defines the contract.
- **Enforcement**: `TweakValidator` enforces it.
- **Mismatch Rule**: Any divergence between schema and code is a bug in code.

---

## 6. API Invariants

### 6.1 Public Interfaces
- **Return Types**: Public methods return only primitive or standard types.
- **Exceptions**:
  - `ValidationError` for contract violations
  - `RuntimeError` for system failures
- Internal exceptions must not leak.

### 6.2 Configuration Handling
- **Immutability**: Loaded tweak definitions are treated as read-only.
- **Isolation**: Validators operate on deep copies to prevent side effects.

---

## 7. Negative Constraints

The engine will **never**:

1. Automatically reboot the system.
2. Automatically resolve or apply dependencies.
3. Suppress errors to report success.
4. Write success states if verification fails.
5. Guess previous system state during rollback.
6. Apply tweaks implicitly without explicit invocation.
7. Mutate history entries after reaching terminal state.
8. Execute Tier 3 tweaks in batches.

---

## 8. Versioning

- **v1.2.0**: Introduction of formal invariants, schema versioning, and state machine enforcement.
- Any modification to this document requires an explicit version bump.
- Breaking invariant changes require a major version increment.
```
