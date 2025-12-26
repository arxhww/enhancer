# EnhancerCore

EnhancerCore is a transactional Windows tweak engine designed to apply, verify, and safely revert system-level configuration changes using declarative JSON files.

The engine guarantees:
- Atomic application of tweaks
- Full rollback on failure
- Persistent history tracking
- Registry state integrity verification

## Features

- Transactional registry modifications
- Automatic rollback on error or failed verification
- SQLite-based tweak history and snapshots
- Declarative tweak definitions (JSON)
- Administrator privilege enforcement
- Optional integrity verification via SHA-256 manifest

## Requirements

### Python mode
- Windows 10 / 11
- Python 3.9+
- Administrator privileges

### Binary mode
- Windows 10 / 11
- Administrator privileges
- No Python installation required

## Usage (Python)

Apply a tweak:
```
python main.py apply tweaks/disable_game_dvr.json
```
Revert a tweak:
```
python main.py revert 011
```
List active tweaks:
```
python main.py list
```

## Usage (Binary)
After building, execute:

- EnhancerCore.exe apply tweaks/disable_game_dvr.json
- EnhancerCore.exe revert 011
- EnhancerCore.exe list

## Tweak Structure

Tweaks are defined as JSON files with explicit apply and verify phases.

Example (simplified):
```
{
  "id": "011",
  "name": "Disable Game DVR",
  "actions": {
    "apply": [...],
    "verify": [...]
  }
}
```
Only JSON files inside the `tweaks/` directory are required to add new functionality.

## Build

To generate a standalone executable:
```
python build.py
```
The output binary will be located in the `dist/` directory along with the `tweaks/` folder.
After building, generate the integrity manifest to be placed next to the executable:

## Integrity Manifest

To generate a cryptographic integrity manifest:
```
python utils/manifest.py
```
The resulting `enhancer_manifest.json` can be used to verify engine integrity.

To verify engine integrity:
```
verify_manifest()
```

## License

This project is provided as-is, without warranty.