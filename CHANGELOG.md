# Changelog

## [v1.2.1-cli]
### Added
- Minimal CLI interface (`python -m cli`) as a thin delegation layer over `TweakManager`.
- Commands: `apply`, `revert`, `list`.

### Constraints
- CLI contains no domain logic.
- No new core dependencies introduced.
- Core (`v1.2.0`) remains unchanged.

## [v1.2.0]
### Added
- Formal state machine with strict lifecycle enforcement.
- Atomic apply/revert with deterministic rollback.
- Schema versioning and invariant validation.
