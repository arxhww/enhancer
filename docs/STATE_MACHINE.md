# EnhancerCore — State Machine Specification

## 1. Purpose

This document defines the **immutable state model** of EnhancerCore (v1.2.0).
It serves as the single source of truth for what states exist, how they transition, and what constitutes a valid workflow.

**Invariant:** Any state or transition not listed here is **IMPOSSIBLE**.

---

## 2. States

### `DEFINED`
*   **Meaning:** Tweak loaded into memory, validated, and ready to apply.
*   **Database Status:** `history.status = 'defined'`
*   **Allowable Actions:** `validate` → `VALIDATED`

### `VALIDATED`
*   **Meaning:** Pre-checks passed, ready to execute.
*   **Database Status:** `history.status = 'validated'`
*   **Allowable Actions:** `apply` → `APPLYING`

### `APPLYING`
*   **Meaning:** System is currently writing changes to disk.
*   **Database Status:** `history.status = 'applying'`
*   **Allowable Actions:** `success` → `APPLIED`, `fail` → `FAILED`, `verify_defer` → `APPLIED_UNVERIFIED`

### `APPLIED`
*   **Meaning:** All actions written. System stable.
*   **Database Status:** `history.status = 'applied'`
*   **Allowable Actions:** `verify` → `VERIFIED`, `revert` → `REVERTED`

### `APPLIED_UNVERIFIED`
*   **Meaning:** Actions written, but verification is deferred (e.g., pending reboot).
*   **Database Status:** `history.status = 'applied_unverified'`
*   **Allowable Actions:** `verify` → `VERIFIED` (after reboot), `revert` → `REVERTED`

### `VERIFIED`
*   **Meaning:** Actions written AND verification passed. System is final.
*   **Database Status:** `history.status = 'verified'`
*   **Allowable Actions:** `revert` → `REVERTED`

### `FAILED`
*   **Meaning:** An operation failed. System is in an error state.
*   **Database Status:** `history.status = 'failed'`
*   **Allowable Actions:** `revert` → `REVERTED`
*   **Note:** Attempting to `apply` from `FAILED` is invalid.

### `REVERTED`
*   **Meaning:** Changes have been rolled back. System is as if the tweak never existed.
*   **Database Status:** `history.status = 'reverted'`
*   **Allowable Actions:** None. This is a terminal state.

### `ORPHANED`
*   **Meaning:** Inconsistent state detected during load. Recovery required.
*   **Database Status:** `history.status = 'orphaned'`
*   **Allowable Actions:** `revert` (Attempt to rollback to last stable state).

---

## 3. Transitions

| Current State | Action | Next State | Condition |
|---------------|--------|-------------|------------|
| `DEFINED` | `validate` | `VALIDATED` | Schema valid. |
| `VALIDATED` | `apply` | `APPLYING` | Composition valid. |
| `APPLYING` | `success` | `APPLIED` | All actions executed. |
| `APPLYING` | `verify_defer` | `APPLIED_UNVERIFIED` | User requested defer or reboot required. |
| `APPLYING` | `fail` | `FAILED` | Exception raised. |
| `APPLIED` | `verify` | `VERIFIED` | Runtime verification passed. |
| `APPLIED` | `revert` | `REVERTED` | User requested rollback. |
| `APPLIED_UNVERIFIED` | `verify` | `VERIFIED` | Post-reboot verification passed. |
| `APPLIED_UNVERIFIED` | `revert` | `REVERTED` | User requested rollback. |
| `VERIFIED` | `revert` | `REVERTED` | User requested rollback. |
| `FAILED` | `revert` | `REVERTED` | User requested rollback. |
| `ORPHANED` | `revert` | `REVERTED` | Emergency cleanup. |

**Note on Implicit Transitions:**
*   `REVERTED` implies successful rollback. The state `APPLIED` or `VERIFIED` is restored (conceptually), but historically it is a new row with status `reverted`.

---

## 4. Invariants (Explicit)

1.  **Single Responsibility:** A `history_id` corresponds to ONE tweak attempt.
2.  **Linear Progress:** A tweak cannot go `APPLYING` -> `DEFINED` without passing through `FAILED` or `REVERTED`.
3.  **Terminal States:** `REVERTED` is terminal. No further transitions allowed.
4.  **Verification Context:** `VERIFIED` implies success. `FAILED` implies error. There is no "verified but failed" state.
```