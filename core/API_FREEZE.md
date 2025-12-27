# EnhancerCore – Public API Freeze

## 1. Purpose

This document defines the **immutable public interface** of EnhancerCore (v1.2.0).

Any modification to the classes, methods, or signatures listed below constitutes a **BREAKING CHANGE** and requires a Major Version Bump (v2.0.0).

**Rule:** If it is not listed here, it is private/internal and subject to change without notice.

---

## 2. Public Classes

### TweakManager

**Location:** `core/tweak_manager.py`

**Constructor:**
```python
def __init__(self) -> None:
    """Initializes validator and runs DB migrations."""
````

**Methods:**

```python
def apply(self, tweak_path: Path) -> bool:
    """
    Applies a single tweak file.

    Returns:
        True if operation succeeded (applied / verified / noop).
        False if validation failed, apply failed, or rollback failed.
    """
```

```python
def revert(self, tweak_id_str: str) -> bool:
    """
    Reverts an active tweak by ID.

    Args:
        tweak_id_str: Modern ID (cat.name@ver) or legacy numeric ID.

    Returns:
        True if revert succeeded.
        False if tweak not found or state machine violation.
    """
```

```python
def list_active(self) -> None:
    """
    Prints active tweaks to stdout.

    LEGACY / CLI-ONLY METHOD
    - Performs direct IO
    - Excluded from architectural guarantees
    - May change or be removed in v2.0.0 without Major bump
    """
```

---

### TweakValidator

**Location:** `core/validation.py`

**Constructor:**

```python
def __init__(self) -> None:
    """Initializes validator with current schema version."""
```

**Methods:**

```python
def validate_definition(self, definition: Dict[str, Any]) -> None:
    """
    Validates a single tweak definition object.

    Raises:
        ValidationError
    """
```

```python
def validate_composition(
    self,
    batch: List[Dict[str, Any]],
    active_tweak_ids: List[str]
) -> None:
    """
    Validates a batch of tweaks for safe execution.

    Raises:
        ValidationError
    """
```

---

### RecoveryManager

**Location:** `core/recovery.py`

**Constructor:**

```python
def __init__(self, auto_recover: bool = True) -> None:
    """Initializes recovery manager."""
```

**Methods:**

```python
def scan_for_issues(self) -> List[Dict]:
    """Returns list of interrupted operations."""
```

```python
def recover_all(self, manager: TweakManager) -> Dict:
    """Executes recovery logic on found issues."""
```

---

## 3. Constants

**File:** `core/constants.py`

```python
SCHEMA_VERSION = 1
ENGINE_VERSION = "1.2.0"
```

* Changing `SCHEMA_VERSION` triggers migration logic.
* Changing `ENGINE_VERSION` follows Semantic Versioning.

---

## 4. Exceptions

### ValidationError

* **Location:** `core/validation.py`
* **Raised by:** `TweakValidator`
* **Type:** subclass of `Exception`

---

## 5. Invariants

1. **Return Types:** All public methods returning `bool` return only `True` or `False`.
2. **Exception Safety:** Public methods raise only `ValidationError` or `RuntimeError`.
3. **Immutability:** Input dictionaries passed to public methods are not mutated.
4. **Version Binding:** `TweakManager` behavior is bound to `SCHEMA_VERSION`.

---

## 6. Enforcement

### Policy

* Signature change in this document → **Major Version Bump (v2.0.0)**
* New public method not listed → **Minor Version Bump (v1.3.0)**

### Mechanism

* `tests/test_api_freeze.py` enforces signature stability.
* Any PR violating this without version bump is rejected.
