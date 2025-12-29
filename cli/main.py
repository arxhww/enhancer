import sys
import argparse
from pathlib import Path

from infra.telemetry.dispatcher import manager as telemetry_manager
from infra.telemetry.logger import LoggerSink
import core.tweak_manager as core_manager
from infra.telemetry.writer import emit as db_emit

def setup_telemetry(log_file=None):
    sink = LoggerSink(log_file)
    telemetry_manager.register_sink(sink)

    def hooked_handler(event, ctx):
        telemetry_manager.dispatch(event, ctx)
        db_emit({
            "event": event,
            "tweak_id": ctx.get("tweak_id"),
            "history_id": ctx.get("history_id"),
            "result": ctx.get("result"),
            "error": ctx.get("error"),
        })

    core_manager._hook = hooked_handler

def cmd_apply(args):
    manager = core_manager.TweakManager()
    sys.exit(0 if manager.apply(Path(args.tweak)) else 1)

def cmd_revert(args):
    manager = core_manager.TweakManager()
    sys.exit(0 if manager.revert(args.tweak_id) else 1)

def cmd_list(args):
    manager = core_manager.TweakManager()
    manager.list_active()
    sys.exit(0)

def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--log-file", type=str, default=None)
    known, unknown = parser.parse_known_args()

    setup_telemetry(log_file=known.log_file)

    parser2 = argparse.ArgumentParser()
    sub = parser2.add_subparsers(dest="command")

    p_apply = sub.add_parser("apply")
    p_apply.add_argument("tweak")

    p_revert = sub.add_parser("revert")
    p_revert.add_argument("tweak_id")

    sub.add_parser("list")

    args = parser2.parse_args(unknown)

    if args.command == "apply":
        cmd_apply(args)
    elif args.command == "revert":
        cmd_revert(args)
    elif args.command == "list":
        cmd_list(args)
    else:
        parser2.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
