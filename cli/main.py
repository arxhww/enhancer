import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.tweak_manager import TweakManager


CMD_HELP = {
    "apply": "Apply a tweak from a JSON definition file.",
    "revert": "Revert an active tweak by ID.",
    "list": "List all currently active tweaks."
}

def cmd_apply(manager, args):
    try:
        success = manager.apply(Path(args.tweak))
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def cmd_revert(manager, args):
    try:
        success = manager.revert(args.tweak_id)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def cmd_list(manager, args):
    try:
        manager.list_active()
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="EnhancerCore CLI v1.2.1")
    subparsers = parser.add_subparsers(dest="command", help="Available sub-commands")

    parser_apply = subparsers.add_parser("apply", help="Apply a tweak")
    parser_apply.add_argument("tweak", type=str, help="Path to JSON tweak file")

    parser_revert = subparsers.add_parser("revert", help="Revert an active tweak")
    parser_revert.add_argument("tweak_id", type=str, help="Tweak ID (e.g. system.disable_search@1.0)")

    parser_list = subparsers.add_parser("list", help="List active tweaks")

    args = parser.parse_args()

    manager = TweakManager()

    if args.command == "apply":
        cmd_apply(manager, args)
    elif args.command == "revert":
        cmd_revert(manager, args)
    elif args.command == "list":
        cmd_list(manager, args)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()