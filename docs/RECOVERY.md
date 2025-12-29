# Recovery System

## Overview

The recovery system is responsible for detecting and normalizing incomplete or inconsistent tweak executions ("zombies") caused by process crashes, power loss, or forced termination.

Recovery operates **fully out-of-band** from the core state machine to ensure system integrity even when the primary logic fails.

---

## Zombie Definition

A **zombie** is any tweak history entry whose status indicates that execution was interrupted before reaching a terminal state.

| Category | States |
| :--- | :--- |
| **Zombie States** | `defined`, `applying`, `verifying`, `failed` |
| **Terminal (Clean) States** | `applied`, `reverted` |

---

## Design Principles

### Out-of-band execution
Recovery never uses `TweakStateMachine`. State machines encode intent; recovery enforces reality. This separation is required for system correctness.

### Idempotency
Recovery can be executed repeatedly without side effects. If a history entry is already normalized, it is skipped.

### Snapshot authority
Rollback snapshots are the single source of truth. Recovery replays rollback actions directly from stored snapshots.

### No inference
Recovery does not attempt to "resume" execution. All zombies are normalized to a safe terminal state to prevent unpredictable behavior.

---

## Recovery Flow

1. **Scan**: Search the database for zombie history entries.
2. **Telemetry**: Emit `recovery.detected` event.
3. **Normalization**: For each zombie:
    * **If `applying` / `verifying` / `failed`**:
        * Execute rollback using snapshots.
        * Mark status as `reverted`.
    * **If `defined`**:
        * Mark status as `failed`.
4. **Resolution**: Emit `recovery.resolved` telemetry.

---

## CLI Usage

```bash
python -m cli.main recover

```

### Exit Codes

* `0`: Success (No zombies found or all recovered successfully).
* `2`: Partial recovery (Some zombies could not be normalized).
* `3`: Recovery failed (Critical system error).

---

## Safety Guarantees

* **No Forced Transitions**: No state machine transitions are forced; recovery bypasses the machine entirely.
* **Isolation**: No active, healthy tweaks are modified.
* **Privilege Integrity**: Recovery never escalates privileges.
* **Auditability**: All actions are fully auditable via telemetry logs.

---

## Rationale

State machines model ideal execution paths, whereas recovery exists to correct non-ideal realities. By keeping recovery logic independent, we ensure that the system can always return to a known stable state regardless of why the previous process failed.
