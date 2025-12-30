# EnhancerCore – Public Contract

## Supported Commands

- apply <tweak>
- revert <tweak_id>
- list
- verify
- recover

## Guarantees

- Commands are idempotent
- Crashes never corrupt state
- Recovery is safe to run repeatedly
- Verification is read-only

## Non-Goals

- No dependency resolution
- No automatic recovery
- No background execution
- No retries

## Stability

The core engine is considered frozen.
Behavior changes require a major version bump.
