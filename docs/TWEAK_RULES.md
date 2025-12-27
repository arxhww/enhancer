# EnhancerCore – Tweak Composition Rules

## 1. Purpose

This document defines the **formal rules governing composition, batching, and execution order** of multiple tweaks.

These rules exist to prevent:
- Silent conflicts between tweaks
- State corruption from invalid execution order
- System instability from incompatible combinations
- Data loss from unsafe batch operations

Rules are **absolute**. Violations cause immediate abort before any system modification.

---

## 2. Fundamental Principles

### 2.1 Isolation by Default

**Rule**: Each tweak executes in isolation unless explicitly batched.

**Rationale**: Independent execution reduces blast radius and simplifies rollback.

**Implication**: Batching is opt-in and subject to strict validation.

---

### 2.2 Explicit Over Implicit

**Rule**: Composition behavior must be declared, not inferred.

**Rationale**: No heuristics. No "the engine will figure it out."

**Implication**: If a composition rule isn't documented here, it's forbidden.

---

### 2.3 Fail Fast

**Rule**: Invalid compositions abort before any tweak applies.

**Rationale**: Partial application of invalid batch is worse than no application.

**Implication**: All validation occurs at composition time, not execution time.

---

## 3. Tier-Based Composition Rules

### 3.1 Tier Isolation

**Rule**: Tweaks of different tiers CANNOT be batched together.

| Batch Attempt | Validity | Reason |
|---------------|----------|--------|
| Tier 0 + Tier 0 | Valid | Same risk profile |
| Tier 1 + Tier 1 | Valid | Same risk profile |
| Tier 0 + Tier 1 | **Invalid** | Risk mismatch |
| Tier 2 + Tier 2 | Valid (with restrictions) | See 3.2 |
| Tier 2 + Tier 3 | **Invalid** | Risk mismatch |
| Tier 3 + Tier 3 | **Invalid** | Never batch experimental |

**Enforcement**: Parse-time rejection of mixed-tier batches.

---

### 3.2 Tier 2 Batch Restrictions

**Rule**: Tier 2 tweaks MAY batch ONLY if:
1. All have `requires_reboot=false`, OR
2. All have `requires_reboot=true`

**Rationale**: Mixing reboot/no-reboot creates ambiguous system state.

**Example**:
```
Valid:   [disable_superfetch, disable_search] (both no-reboot)
Valid:   [optimize_tcp, modify_boot_timeout] (both reboot)
Invalid: [disable_superfetch, optimize_tcp] (mixed reboot)
```

---

### 3.3 Tier 3 Execution

**Rule**: Tier 3 tweaks MUST execute individually with explicit per-tweak confirmation.

**Rationale**: Experimental changes require isolated risk assessment.

**Implication**: No batch mode. No automation. Manual only.

---

## 4. Rollback Guarantee Rules

### 4.1 No Mixed Guarantees

**Rule**: Cannot batch tweaks with different `rollback_guaranteed` values.

| Batch Attempt | Validity | Reason |
|---------------|----------|--------|
| `true` + `true` | Valid | Uniform rollback capability |
| `false` + `false` | Valid | User accepts no rollback |
| `true` + `false` | **Invalid** | Cannot guarantee partial rollback |

**Rationale**: Partial rollback creates undefined system state.

---

### 4.2 Non-Guaranteed Tweaks Require Isolation

**Rule**: Tweaks with `rollback_guaranteed=false` MUST execute individually.

**Rationale**: Cannot mix reversible and irreversible changes in same transaction.

**Implication**: These tweaks are never batchable, even with each other.

---

## 5. Scope-Based Composition Rules

### 5.1 Boot Scope Isolation

**Rule**: Tweaks with `scope` containing `boot` MUST NOT batch with non-boot tweaks.

**Rationale**: Boot config changes operate at different system layer.

**Example**:
```
Invalid: [disable_game_dvr (registry), modify_bcdedit (boot)]
Valid:   [modify_bcdedit (boot), disable_hpet (boot)]
```

---

### 5.2 Scope Conflict Detection

**Rule**: Tweaks modifying the same scope MUST check for conflicts.

**Conflict Definition**: Two tweaks conflict if:
1. Same scope overlap, AND
2. Listed in each other's `conflicts_with` field

**Enforcement**: Hard block at composition time.

**Example**:
```json
// Tweak A
{
  "id": "performance.disable_superfetch@1.0",
  "scope": ["service"],
  "conflicts_with": ["performance.enable_superfetch"]
}

// Tweak B (attempting to apply)
{
  "id": "performance.enable_superfetch@1.0",
  "scope": ["service"],
  "conflicts_with": ["performance.disable_superfetch"]
}

// Result: REJECT - explicit conflict
```

---

### 5.3 Multi-Scope Complexity Limit

**Rule**: Cannot batch more than 2 tweaks if any has `scope` length ≥ 3.

**Rationale**: High-complexity tweaks increase interaction risk.

**Example**:
```
Invalid: [tweak_A (3 scopes), tweak_B (2 scopes), tweak_C (1 scope)]
Valid:   [tweak_A (3 scopes), tweak_B (1 scope)]
```

---

## 6. Execution Order Rules

### 6.1 Deterministic Order

**Rule**: Batch execution order is deterministic and based on:
1. Tier (ascending: 0 → 1 → 2)
2. Scope complexity (ascending: 1 scope → N scopes)
3. ID lexicographic order

**Rationale**: Predictable execution. Reproducible results.

**Implication**: User cannot control order within a batch.

---

### 6.2 Dependency Resolution

**Rule**: If tweak B lists tweak A in `dependencies`, then:
- A must be applied before B
- A must be currently active when B applies
- Engine does NOT auto-apply dependencies

**Enforcement**:
- Composition-time check: dependencies are active
- If not active: abort with error

**Example**:
```json
{
  "id": "privacy.disable_cortana@1.0",
  "dependencies": ["privacy.disable_search"]
}

// If privacy.disable_search is not active:
// ERROR: Dependency not satisfied. Apply privacy.disable_search first.
```

---

### 6.3 No Circular Dependencies

**Rule**: Circular dependencies are invalid.

**Detection**: Composition-time graph cycle check.

**Example**:
```
A depends on B
B depends on A
→ INVALID
```

---

## 7. Verification Semantics Rules

### 7.1 Uniform Verification

**Rule**: All tweaks in batch must have same `verify_semantics`.

| Batch Attempt | Validity | Reason |
|---------------|----------|--------|
| `runtime` + `runtime` | Valid | Immediate verification |
| `persisted` + `persisted` | Valid | Deferred to reboot |
| `deferred` + `deferred` | Valid | No verification |
| `runtime` + `persisted` | **Invalid** | Mixed verification timing |

**Rationale**: Cannot verify some tweaks immediately and others later in same transaction.

---

### 7.2 Deferred Verification Isolation

**Rule**: Tweaks with `verify_semantics=deferred` SHOULD execute individually.

**Rationale**: No verification means no guarantee. Isolation reduces risk.

**Exception**: Multiple deferred tweaks MAY batch if:
- All are tier 0 or tier 1
- All have `rollback_guaranteed=true`

---

## 8. Abort Conditions

### 8.1 Pre-Apply Abort

Engine MUST abort before any action if:

1. **Conflict detected**: Active tweak in `conflicts_with` list
2. **Dependency unsatisfied**: Required tweak not active
3. **Tier mismatch**: Mixed tiers in batch
4. **Rollback mismatch**: Mixed rollback guarantees
5. **Scope violation**: Boot + non-boot mix
6. **Verification mismatch**: Mixed verification semantics
7. **Invalid metadata**: Schema validation failure
8. **Tier 3 batch**: Attempting to batch experimental tweaks

**Enforcement**: All checks run before first snapshot.

---

### 8.2 Mid-Apply Abort

Engine MUST abort during execution if:

1. **Snapshot failure**: Cannot capture current state
2. **Apply failure**: Action throws exception
3. **Verification failure**: Post-apply state doesn't match expected

**Behavior**: Immediate rollback of all applied actions in reverse order.

---

### 8.3 Abort Guarantees

After abort:
- **No partial application**: All-or-nothing per batch
- **State restored**: Rollback to pre-batch state
- **History recorded**: Abort reason logged in database
- **User notified**: Clear error message with cause

---

## 9. Batch Size Limits

### 9.1 Hard Limits

**Rule**: Maximum batch sizes by tier:

| Tier | Max Batch Size | Rationale |
|------|----------------|-----------|
| 0 | 20 | Low risk, allow bulk operations |
| 1 | 10 | Moderate risk, reasonable batch |
| 2 | 3 | High risk, small batches only |
| 3 | 1 | Experimental, never batch |

**Enforcement**: Composition-time rejection if exceeded.

---

### 9.2 Action Count Limits

**Rule**: Maximum total actions per batch: 50

**Rationale**: 
- Snapshot time grows linearly with actions
- Rollback complexity grows with action count
- User attention span limited

**Calculation**: Sum of all actions across all tweaks in batch.

**Example**:
```
Tweak A: 5 actions
Tweak B: 8 actions
Tweak C: 40 actions
Total: 53 actions → REJECT (exceeds limit)
```

---

## 10. Reboot Handling

### 10.1 Reboot Batch Homogeneity

**Rule**: All tweaks in batch must have same `requires_reboot` value.

**Rationale**: Cannot have "apply now" and "apply after reboot" in same transaction.

---

### 10.2 Reboot Sequence

For batches with `requires_reboot=true`:

1. Apply all tweaks
2. Verify all tweaks (persisted verification)
3. Prompt user for reboot
4. **DO NOT auto-reboot**

**Critical**: Engine never reboots automatically.

---

### 10.3 Post-Reboot Verification

**Rule**: Engine CANNOT verify `requires_reboot=true` tweaks after reboot.

**Rationale**: 
- New process, no history context
- Snapshots don't persist across reboots
- Verification must happen before reboot

**Implication**: `requires_reboot=true` typically uses `verify_semantics=persisted`.

---

## 11. Special Composition Cases

### 11.1 Conflict Mutual Exclusion

**Rule**: If tweaks A and B conflict, applying B must:
1. Check if A is active
2. If active: abort with error
3. User must manually revert A before applying B

**No Automatic Resolution**: Engine does not auto-revert conflicts.

---

### 11.2 Upgrade Scenarios

**Rule**: Applying tweak A@2.0 when A@1.0 is active:
1. Check if base IDs match (`category.name`)
2. If match: abort with error
3. User must revert A@1.0 before applying A@2.0

**Rationale**: Upgrades are explicit revert + apply, not automatic.

---

### 11.3 Empty Batches

**Rule**: Batch with zero tweaks is invalid.

**Enforcement**: Composition-time rejection.

---

## 12. Rule Precedence

When rules conflict, precedence order:

1. **Safety rules** (abort conditions, rollback guarantees)
2. **Tier rules** (isolation, batch limits)
3. **Scope rules** (boot isolation, conflicts)
4. **Verification rules** (semantics matching)
5. **Size limits** (batch/action counts)

**Example**: If tier rule says "allow batch" but safety rule says "abort", abort wins.

---

## 13. Enforcement Points

### 13.1 Composition Time

- Tier matching
- Rollback guarantee matching
- Scope conflict detection
- Dependency validation
- Batch size limits
- Metadata schema validation

**Result**: Accept batch or reject with specific error.

---

### 13.2 Execution Time

- Snapshot success
- Apply success
- Verification success

**Result**: Continue or abort with rollback.

---

### 13.3 No Runtime Decisions

**Rule**: All composition logic runs before first action.

**Rationale**: Cannot discover incompatibility after partial application.

---

## 14. Rule Evolution

### 14.1 Adding Rules

New rules MAY be added if:
- They increase safety
- They are backward-compatible (reject more, not less)
- They are documented in this file

### 14.2 Relaxing Rules

Relaxing existing rules REQUIRES:
- Major version bump
- Migration documentation
- Justification of reduced safety

### 14.3 Rule Versioning

This document is version 1.0.

Future versions must:
- Increment version number
- Document all rule changes
- Provide migration path for existing tweaks

---

## 15. Non-Goals

This document does NOT define:
- Metadata schema (see TWEAK_SCHEMA.md)
- State machine semantics (see STATES.md)
- Action implementation (see Action interface)
- Benchmarking methodology (see BENCHMARK_SPEC.md)

This is **composition logic only**. Execution semantics are separate.