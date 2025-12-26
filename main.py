#!/usr/bin/env python3
"""
EnhancerCore v1.0
Transactional Windows Tweak Engine – CLI Entry Point
"""

import sys
from pathlib import Path
from utils.admin import require_admin
from core.tweak_manager import TweakManager

def print_usage():
    print("""
USAGE:
    python main.py apply <tweak.json>     - Apply a tweak
    python main.py revert <tweak_id>      - Revert a previously applied tweak
    python main.py list                   - List active tweaks

EXAMPLES:
    python main.py apply tweaks/disable_game_dvr.json
    python main.py revert 011
    python main.py list
    """)

def main():
    require_admin()
    
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    manager = TweakManager()
    
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
    
    else:
        print(f"ERROR: Unknown command: {command}")
        print_usage()
        sys.exit(1)

if __name__ == "__main__":
    main()