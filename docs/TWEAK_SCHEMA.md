# EnhancerCore – Tweak Metadata Schema

## 1. Purpose

This document defines the **mandatory and optional metadata fields** that govern tweak execution semantics.

Metadata exists to make execution decisions **explicit and verifiable before code runs**.

A human reading a tweak definition must be able to predict:
- What the system will do
- What risks exist
- What guarantees apply
- Whether reboot is required
- Whether rollback is possible

---

## 2. Mandatory Fields

Every tweak MUST define these fields. Missing mandatory fields invalidate the tweak.

### 2.1 `id`

**Type**: `string`  
**Format**: `category.name@version` or legacy numeric  
**Example**: `performance.disable_superfetch@1.0`

**Semantics**:
- Unique identifier for the tweak
- Used for deduplication and version management
- Must not change between revisions (only version component changes)

---

### 2.2 `name`

**Type**: `string`  
**Max Length**: 80 characters  
**Example**: `"Disable Windows Superfetch Service"`

**Semantics**:
- Human-readable display name
- Used in logs, UI, and reports
- Must be descriptive, not promotional

---

### 2.3 `description`

**Type**: `string`  
**Max Length**: 300 characters  
**Example**: `"Disables Superfetch/SysMain service to reduce disk I/O on SSDs"`

**Semantics**:
- Explains what the tweak does and why
- Must state the intended effect, not the mechanism
- Should mention relevant hardware/software contexts

---

### 2.4 `tier`

**Type**: `integer`  
**Valid Values**: `0 | 1 | 2 | 3`  
**Example**: `1`

**Semantics**:

| Tier | Meaning | Characteristics | Examples |
|------|---------|-----------------|----------|
| **0** | **Cosmetic** | No performance impact. UI preferences only. Fully reversible at runtime. | Theme changes, explorer options |
| **1** | **Safe Optimization** | Documented, widely-used tweaks. No system stability risk. Reversible without reboot. | Disable telemetry, Game DVR off |
| **2** | **Aggressive Optimization** | Modifies services or boot config. May require reboot. Reversible but with potential side effects. | Disable Superfetch, modify power plan |
| **3** | **Experimental/Dangerous** | Undocumented changes. Potential for system instability. Reboot often required. Rollback not guaranteed. | Boot config edits, kernel patches |

**Critical Distinction**:
- **Tier controls execution policy** (batching, confirmation, automation)
- **Risk level controls user-facing warnings and disclosure** (UI, logs, prompts)

These are separate concerns. Tier governs what the engine does. Risk level governs what the user sees.

**Execution Rules**:
- Tier 3 requires explicit user confirmation
- Tier 2+ cannot execute in batch mode without --force
- Tier 0-1 can be applied automatically

---

### 2.5 `risk_level`

**Type**: `enum`  
**Valid Values**: `"low" | "medium" | "high"`  
**Example**: `"medium"`

**Semantics**:

| Level | Definition | Characteristics |
|-------|------------|-----------------|
| **low** | No known stability issues. Change is localized and well-understood. | Registry-only tweaks with no service dependencies |
| **medium** | May cause application compatibility issues or require configuration adjustment. | Service modifications, power config changes |
| **high** | Risk of system instability, boot failure, or data loss if misconfigured. | Boot config, kernel settings, driver modifications |

**Relationship to Tier**:
- `tier >= 2` MUST have `risk_level >= medium`
- `tier == 3` SHOULD have `risk_level == high` unless extensively tested

---

### 2.6 `requires_reboot`

**Type**: `boolean`  
**Example**: `false`

**Semantics**:
- `true`: Changes take effect only after system restart
- `false`: Changes take effect immediately

**Rules**:
- If `true`, engine SHOULD prompt user before continuing
- Tweaks with `requires_reboot=true` SHOULD NOT be batched with `false` tweaks
- Rollback of rebooted changes may require additional reboot
- **Engine must NOT auto-reboot under any circumstances**

---

### 2.7 `rollback_guaranteed`

**Type**: `boolean`  
**Example**: `true`

**Semantics**:
- `true`: Engine can fully restore previous state via stored snapshots
- `false`: Rollback may be incomplete or impossible

**When `false` is valid**:
- External state that cannot be snapshotted (e.g., downloaded files)
- Actions with irreversible side effects (e.g., Windows Update removal)
- Actions that modify state outside engine scope (e.g., third-party software)

**Rules**:
- Tweaks with `rollback_guaranteed=false` MUST NOT execute without explicit confirmation
- Cannot be batched with other tweaks
- `tier=3` often implies `rollback_guaranteed=false`

---

### 2.7.1 `rollback_limitations` (Optional, required if `rollback_guaranteed=false`)

**Type**: `enum` or `list[enum]`  
**Valid Values**: `"external_state" | "one_way_operation" | "third_party_dependency" | "partial_restore"`  
**Example**: `["external_state", "one_way_operation"]`

**Semantics**:

| Limitation | Definition |
|------------|------------|
| **external_state** | Modifies files, downloads, or state outside registry/services |
| **one_way_operation** | Inherently irreversible (e.g., deletion, uninstallation) |
| **third_party_dependency** | Depends on software/config outside Windows |
| **partial_restore** | Can restore some but not all previous state |

**Rules**:
- MUST be present if `rollback_guaranteed=false`
- Used for categorization and tooling
- Avoids vague "rollback not guaranteed" explanations

---

### 2.8 `scope`

**Type**: `list[enum]`  
**Valid Values**: `"registry" | "service" | "power" | "boot" | "filesystem" | "network"`  
**Example**: `["registry", "service"]`

**Semantics**:

| Scope | Definition |
|-------|------------|
| **registry** | Only modifies Windows Registry |
| **service** | Modifies Windows service configuration |
| **power** | Modifies power management settings (powercfg) |
| **boot** | Modifies boot configuration (bcdedit) |
| **filesystem** | Modifies file permissions or attributes |
| **network** | Modifies network stack or firewall |

**Rules**:
- Must be explicit list, never a single "mixed" value
- Used for conflict detection between tweaks
- `scope` containing `boot` MUST have `requires_reboot=true`
- If scope list length ≥ 3, engine MAY treat tweak as high-complexity implicitly
- Multiple scopes increase execution risk and reduce batching eligibility

---

### 2.9 `verify_semantics`

**Type**: `enum`  
**Valid Values**: `"runtime" | "persisted" | "deferred"`  
**Example**: `"runtime"`

**Semantics**:

| Semantic | Definition | Verification Timing |
|----------|------------|---------------------|
| **runtime** | Effect is immediately verifiable in system state | Immediately after apply |
| **persisted** | Effect is written to disk but only active after event (e.g., reboot) | After apply, before reboot |
| **deferred** | Effect cannot be verified until external condition (e.g., service restart, user action) | Verification skipped or delayed |

**Rules**:
- `requires_reboot=true` often implies `verify_semantics=persisted`
- `verify_semantics=deferred` REQUIRES `verify_notes` field (see 2.9.1)
- Engine verification MUST respect semantic expectation

---

### 2.9.1 `verify_notes` (Optional, required if `verify_semantics=deferred`)

**Type**: `string`  
**Max Length**: 200 characters  
**Example**: `"Service restart required. Verification possible after next system reboot."`

**Semantics**:
- Explains why verification is deferred
- States conditions under which verification becomes possible
- MUST be present if `verify_semantics=deferred`

**Rules**:
- Used for audit trail and documentation
- Not parsed by engine, but required for human review
- Prevents vague "deferred" without explanation

---

## 3. Optional Fields

These fields provide additional context but are not required for execution.

### 3.1 `category`

**Type**: `string`  
**Example**: `"performance"`

**Semantics**:
- Organizational metadata for UI/filtering
- Should match ID prefix for modern IDs
- Not used in execution logic

---

### 3.2 `impact`

**Type**: `enum`  
**Valid Values**: `"low" | "medium" | "high"`  
**Example**: `"medium"`

**Semantics**:
- Subjective measure of noticeable effect
- `low`: Minimal perceptible change
- `medium`: Noticeable improvement in specific scenarios
- `high`: Dramatic system behavior change

**Note**: This is NOT `risk_level`. Impact measures benefit, not danger.

---

### 3.3 `compatible_with`

**Type**: `list[string]`  
**Example**: `["windows_10_22h2", "windows_11_23h2"]`

**Semantics**:
- OS/version compatibility declarations
- Engine does NOT enforce this (informational only)
- Format is freeform but should be consistent within project

---

### 3.4 `conflicts_with`

**Type**: `list[string]`  
**Example**: `["performance.enable_superfetch"]`

**Semantics**:
- List of tweak IDs that should not coexist
- Mutual exclusion enforcement

**Conflict Resolution**:
- **Hard block**: Engine MUST prevent execution if conflict is active
- **Not a warning**: Conflicts are absolute, not advisory
- User must revert conflicting tweak before applying new one

**Rules**:
- Conflicts are bidirectional (if A conflicts with B, B conflicts with A)
- Engine SHOULD validate bidirectionality at parse time

---

### 3.5 `dependencies`

**Type**: `list[string]`  
**Example**: `["system.disable_defender@1.0"]`

**Semantics**:
- Tweaks that must be applied before this one
- Engine does NOT auto-apply dependencies (user must apply manually)
- Used for validation only

---

### 3.6 `author`

**Type**: `string`  
**Example**: `"EnhancerCore Team"`

**Semantics**:
- Attribution metadata
- Not used in execution

---

### 3.7 `source_url`

**Type**: `string` (URL)  
**Example**: `"https://docs.microsoft.com/en-us/windows/privacy/..."`

**Semantics**:
- Reference to authoritative documentation
- Used for verification and trust

---

## 4. Validation Rules

### 4.1 Field Consistency

The following combinations are **invalid**:

| Invalid Combination | Reason |
|---------------------|--------|
| `tier=0` + `requires_reboot=true` | Cosmetic changes don't require reboot |
| `tier=3` + `rollback_guaranteed=true` | Experimental changes rarely guarantee rollback |
| `scope` contains `boot` + `requires_reboot=false` | Boot config always requires reboot |
| `risk_level=low` + `tier=3` | Tier 3 is inherently high risk |
| `verify_semantics=runtime` + `requires_reboot=true` | Runtime verification impossible if reboot needed |
| `rollback_guaranteed=false` + missing `rollback_limitations` | Must categorize limitation type |
| `verify_semantics=deferred` + missing `verify_notes` | Must explain deferral reason |

### 4.2 Required Field Combinations

The following combinations are **required**:

| Condition | Required Field |
|-----------|----------------|
| `tier >= 2` | `risk_level >= medium` |
| `scope` contains `boot` | `requires_reboot=true` |
| `rollback_guaranteed=false` | `rollback_limitations` field |
| `verify_semantics=deferred` | `verify_notes` field |

---

## 5. Example: Complete Metadata

```json
{
  "id": "performance.disable_superfetch@1.0",
  "name": "Disable Superfetch Service",
  "description": "Disables SysMain service to reduce disk I/O on SSDs. May impact HDD performance negatively.",
  "tier": 2,
  "risk_level": "medium",
  "requires_reboot": false,
  "rollback_guaranteed": true,
  "scope": ["registry", "service"],
  "verify_semantics": "runtime",
  
  "category": "performance",
  "impact": "medium",
  "compatible_with": ["windows_10", "windows_11"],
  "conflicts_with": ["performance.enable_superfetch"],
  "dependencies": [],
  "author": "EnhancerCore Team",
  "source_url": "https://docs.microsoft.com/en-us/windows-server/administration/performance-tuning/"
}
```

### Example: Tweak with Rollback Limitations

```json
{
  "id": "system.remove_onedrive@1.0",
  "name": "Remove OneDrive Integration",
  "description": "Uninstalls OneDrive client and removes system integration. Cannot be undone via rollback.",
  "tier": 3,
  "risk_level": "high",
  "requires_reboot": true,
  "rollback_guaranteed": false,
  "rollback_limitations": ["one_way_operation", "external_state"],
  "scope": ["registry", "filesystem"],
  "verify_semantics": "persisted",
  
  "category": "privacy",
  "impact": "high"
}
```

### Example: Tweak with Deferred Verification

```json
{
  "id": "network.optimize_tcp_stack@1.0",
  "name": "Optimize TCP/IP Stack",
  "description": "Applies TCP window scaling and congestion control optimizations.",
  "tier": 2,
  "risk_level": "medium",
  "requires_reboot": true,
  "rollback_guaranteed": true,
  "scope": ["network", "registry"],
  "verify_semantics": "deferred",
  "verify_notes": "Network stack changes only testable after reboot and under network load.",
  
  "category": "performance",
  "impact": "medium"
}
```

---

## 6. Metadata Evolution

### 6.1 Adding Fields

New optional fields MAY be added without breaking existing tweaks.

New mandatory fields REQUIRE a schema version bump and migration path.

**Schema Versioning**:
- Future versions MAY include `schema_version` field in tweak definitions
- Current schema is implicitly version 1.0
- Version changes require documented migration procedures

### 6.2 Removing Fields

Mandatory fields MUST NOT be removed.

Optional fields may be deprecated with 2-version notice period.

### 6.3 Changing Semantics

Semantic changes to existing fields require major version bump.

---

## 7. Enforcement

This schema is **authoritative**.

Any tweak violating these rules is **invalid by definition**.

Enforcement occurs at:
1. **Parse time**: Schema validation before execution
2. **Apply time**: Consistency checks before modification
3. **Composition time**: Conflict detection between tweaks

---

## 8. Non-Goals

This schema does NOT define:
- How actions are implemented (see Action interface)
- State machine semantics (see STATES.md)
- Composition rules (see TWEAK_RULES.md)

This is **metadata only**. Execution semantics are separate.