# EnhancerCore – Internal Side Effects Audit

**Date:** 2024-05-23  
**Scope:** Core Engine (`core/`)  
**Status:** DRAFT (Pending Review)

## 1. Purpose

This document inventories all internal side effects, state mutations, and control flow logic currently present in the codebase.

**Goal:** To identify implicit behaviors before refactoring (Executor isolation) or hardening (Time abstraction).

---

## 2. State Write Operations (I/O & Persistence)

### 2.1 Direct Database Writes (SQLite)

**Location:** `core/rollback.py`

| Function | Table | Trigger | Implicit Behavior |
|----------|-------|---------|------------------|
| `init_db()` | `tweak_history`, `snapshots`, `snapshots_v2` | Module import | Creates schema if missing. Implicit side effect on import. |
| `create_history_entry()` | `tweak_history` | Apply start | Sets `status='pending'`, `applied_at=now`. |
| `save_snapshot_v2()` | `snapshots_v2` | After apply action | Serializes `ActionSnapshot` to JSON. |
| `mark_applying()` | `tweak_history` | State transition | Sets `status='applying'`. |
| `mark_success()` | `tweak_history` | Successful apply | Sets `status='applied'`. |
| `mark_rolled_back()` | `tweak_history` | Apply failure | Sets `status='rolled_back'`, writes `error_message`. |
| `mark_reverted()` | `tweak_history` | Manual revert | Sets `status='reverted'`, sets `reverted_at=now`. |
| `mark_noop()` | `tweak_history` | Pre-check noop | Sets `status='noop'`. |

**Observations:**
- Multiple writers to `tweak_history.status`:
  - `TweakStateMachine` (primary authority)
  - `rollback.py` legacy functions
- Risk of desynchronization if both paths are used.
- `init_db()` executes on import, causing implicit side effects.

---

### 2.2 Registry Writes (System State)

**Location:** `core/actions/registry_action.py`

| Function | Trigger | Fallback | Risk |
|---------|---------|----------|------|
| `set_value()` | `apply()` | `winreg.CreateKeyEx`, `SetValueEx` | Registry corruption if path invalid. |
| `delete_value()` | `rollback()` | Silent success if missing key | Assumes idempotency. |

**Observations:**
- Registry errors propagate as `OSError` / `WindowsError`.
- Rollback relies on stored previous value.
- Assumes atomicity per value (not guaranteed across batches).

---

### 2.3 Service / Power / Boot Writes

**Location:** `core/actions/*.py`

| Component | Trigger | Risk |
|---------|---------|------|
| `ServiceAction` | `apply()` | Service restart may hang. |
| `PowerCfgAction` | `apply()` | External process dependency. |
| `BcdEditAction` | `apply()` | Boot configuration corruption. |

**Observations:**
- `subprocess.run` is synchronous.
- No timeouts configured.

---

## 3. Control Flow & Decision Logic

### 3.1 TweakManager (Orchestrator)

**Location:** `core/tweak_manager.py`

| Method | Implicit Decision | Side Effect |
|------|------------------|-------------|
| `apply()` | Early exit if pre-check verify passes | No DB entry created. |
| `apply()` | Rollback on exception | Alters DB state. |
| `revert()` | Linear scan of active tweaks | O(N) DB read. |

**Observations:**
- `apply()` mixes IO, control flow, and execution.
- Missing verify list implies assumed success in runtime mode.

---

### 3.2 Validation Logic

**Location:** `core/validation.py`

| Method | Implicit Decision | Effect |
|------|------------------|--------|
| `validate_composition()` | Uses `active_tweak_ids` | Requires fresh DB state. |
| `_check_non_guaranteed_isolation()` | Enforces single-item batch | Restricts execution flow. |

---

## 4. Temporal Coupling (Time Dependencies)

### 4.1 Direct Time Usage

| Component | Usage | Type |
|---------|------|------|
| `rollback.py` | `datetime.now()` | Wall-clock time. |
| `state_machine.py` | `datetime.now()` | Wall-clock time. |

**Risks:**
- Non-deterministic tests.
- Clock skew issues.
- No replayability.

---

## 5. Hidden State & Globals

| Variable | Location | Scope | Risk |
|---------|----------|-------|------|
| `DB_PATH` | `rollback.py`, `state_machine.py` | Module global | Multiple DB handles. |
| `ACTION_REGISTRY` | `actions/factory.py` | Module global | Mutable runtime registry. |

---

## 6. Error Swallowing & Broad Catches

| Location | Pattern | Risk |
|---------|---------|------|
| `tweak_manager.py` | `except Exception` | Masks system-level errors. |
| `registry_action.py` | `except OSError` | Masks permission vs absence. |

---

## 7. Action Logic Coupling

| Action | Dependency | Reason |
|------|------------|--------|
| `ServiceAction` | `pywin32` | External native binding. |
| `PowerCfgAction` | `powercfg.exe` | System binary dependency. |

---

## 8. Summary of Debt

1. Double authority over DB state.
2. Implicit best-effort success paths.
3. Global duplicated configuration.
4. Hard time coupling.
5. Overly broad exception handling.

---

## 9. Classification

- **Allowed (Keep):** State persistence via `TweakStateMachine`.
- **Allowed (Keep):** Deterministic system writes.
- **Transient (Migrate):** `rollback.py` legacy helpers.
- **Forbidden (Refactor):** Broad `except Exception`, direct `datetime.now()` in logic.
