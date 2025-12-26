#!/usr/bin/env python3
"""
EnhancerCore v1.1
Transactional Windows Tweak Engine with Recovery System
"""

import sys
from pathlib import Path
from utils.admin import require_admin
from core.tweak_manager import TweakManager
from core.recovery import RecoveryManager


def print_usage():
    print("""
USAGE:
    python main.py apply <tweak.json>     - Apply a tweak
    python main.py revert <tweak_id>      - Revert a previously applied tweak
    python main.py list                   - List active tweaks
    python main.py recover                - Scan and recover interrupted operations

EXAMPLES:
    python main.py apply tweaks/gaming.disable_game_dvr@1.0.json
    python main.py revert gaming.disable_game_dvr
    python main.py list
    python main.py recover
    
TWEAK ID FORMATS:
    Modern:  category.name@version  (e.g., gaming.disable_game_dvr@1.0)
    Legacy:  numeric ID              (e.g., 011) - auto-converted to modern format
    """)


def run_recovery_check(manager: TweakManager):
    """Run recovery scan on startup."""
    recovery = RecoveryManager(auto_recover=True)
    
    print("\n[STARTUP] Scanning for interrupted operations...")
    issues = recovery.scan_for_issues()
    
    if not issues:
        print("[OK] No issues found")
        return
    
    print(f"\n[WARNING] Found {len(issues)} interrupted operation(s)")
    
    results = recovery.recover_all(manager)
    
    print(f"\n[RECOVERY SUMMARY]")
    print(f"  Issues found: {results['issues_found']}")
    print(f"  Recovered: {results['recovered']}")
    print(f"  Failed: {results['failed']}")
    
    if results['failed'] > 0:
        print(f"\n[WARNING] Some recoveries failed. Check logs for details.")


def main():
    require_admin()
    
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    manager = TweakManager()
    
    if command != "recover":
        run_recovery_check(manager)
    
    if command == "apply":
        if len(sys.argv) < 3:
            print("ERROR: Missing tweak file path.")
            print_usage()
            sys.exit(1)
        
        tweak_path = Path(sys.argv[2])
        if not tweak_path.exists():
            print(f"ERROR: File not found: {tweak_path}")
            sys.exit(1)
        
        success = manager.apply(tweak_path)
        sys.exit(0 if success else 1)
    
    elif command == "revert":
        if len(sys.argv) < 3:
            print("ERROR: Missing tweak ID.")
            print_usage()
            sys.exit(1)
        
        tweak_id = sys.argv[2]
        success = manager.revert(tweak_id)
        sys.exit(0 if success else 1)
    
    elif command == "list":
        manager.list_active()
        sys.exit(0)
    
    elif command == "recover":
        print("\n[MANUAL RECOVERY MODE]")
        recovery = RecoveryManager(auto_recover=True)
        results = recovery.recover_all(manager)
        
        print(f"\n[RECOVERY COMPLETE]")
        print(f"  Recovered: {results['recovered']}")
        print(f"  Failed: {results['failed']}")
        
        sys.exit(0 if results['failed'] == 0 else 1)
    
    else:
        print(f"ERROR: Unknown command: {command}")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()