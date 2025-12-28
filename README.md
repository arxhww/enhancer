# EnhancerCore v1.2.1 - CLI Interface

**Formal State Machine v1.2.0 Core + Minimal CLI Interface.**

EnhancerCore is a system-wide tweak engine for Windows 11. It ensures reliability through a formal state machine, idempotent operations, and atomic database transactions.

## Installation

1. Clone the repository.
2. No external dependencies required. Python ≥ 3.10.
3. Initialize database (automatic on first run).

## Usage

The `cli` tool is the recommended user interface for EnhancerCore.

### Apply a Tweak

Applies a tweak definition file via `TweakManager`.

```bash
python -m cli apply <tweak_path>
```

### Revert a Tweak

Reverts an active tweak (Legacy ID or Modern ID) via `TweakManager`.

```bash
python -m cli revert <tweak_id>
```

### List Active Tweaks

Lists all currently active tweaks.

```bash
python -m cli list
```

## Core API

For developers, the core logic is encapsulated in `TweakManager` and `TweakStateMachine`.

```python
from core.tweak_manager import TweakManager

manager = TweakManager()
# manager.apply(...)
# manager.revert(...)
```