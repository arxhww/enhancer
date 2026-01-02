import sys
import argparse
from pathlib import Path

from infra.telemetry.dispatcher import manager as telemetry_manager
from infra.telemetry.logger import LoggerSink
from infra.telemetry.writer import emit as db_emit

import core.tweak_manager as core_manager
from infra.verify.detector import run_verification


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
            "error": str(ctx.get("error")) if ctx.get("error") else None,
        })

    core_manager._hook = hooked_handler


def cmd_apply(args):
    manager = core_manager.TweakManager()

    if args.dry_run:
        ok = manager.dry_run(Path(args.tweak))
        sys.exit(0 if ok else 1)

    sys.exit(0 if manager.apply(Path(args.tweak)) else 1)


def cmd_revert(args):
    manager = core_manager.TweakManager()
    sys.exit(0 if manager.revert(args.tweak_id) else 1)


def cmd_list(args):
    manager = core_manager.TweakManager()
    manager.list_active()
    sys.exit(0)


def cmd_verify(_args):
    invalid = run_verification()
    sys.exit(0 if not invalid else 2)


def cmd_recover(args):
    manager = core_manager.TweakManager()
    result = manager.recover()

    detected = result["detected"]
    recovered = result["recovered"]

    if detected == 0:
        sys.exit(0)
    if recovered == detected:
        sys.exit(0)
    if recovered > 0:
        sys.exit(2)
    sys.exit(3)
    
def cmd_reexplain(args):
    manager = core_manager.TweakManager()
    manager.reexplain(Path(args.tweak))
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--log-file", type=str, default=None)
    known, unknown = parser.parse_known_args()

    setup_telemetry(log_file=known.log_file)

    parser2 = argparse.ArgumentParser()
    sub = parser2.add_subparsers(dest="command")

    sub.add_parser("recover")
    sub.add_parser("verify")
    sub.add_parser("list")

    p_apply = sub.add_parser("apply")
    p_apply.add_argument("tweak")
    p_apply.add_argument("--dry-run", action="store_true")
    
    p_reexplain = sub.add_parser("reexplain")
    p_reexplain.add_argument("tweak")


    p_revert = sub.add_parser("revert")
    p_revert.add_argument("tweak_id")

    args = parser2.parse_args(unknown)

    if args.command == "apply":
        cmd_apply(args)
    elif args.command == "revert":
        cmd_revert(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "recover":
        cmd_recover(args)
    elif args.command == "verify":
        cmd_verify(args)
    elif args.command == "reexplain":
        cmd_reexplain(args)
    else:
        parser2.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
