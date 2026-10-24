from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from collections.abc import Sequence

from auto_bean.common import WorkflowError, workspace
from auto_bean.init import initialize
from auto_bean.migrate import apply_migration, plan_migration
from auto_bean.runtime import TOOLS, ensure_runtime, run_tool


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Internal auto-bean plugin helper")
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("serve")
    validation = commands.add_parser("validate")
    validation.add_argument("--workspace", type=Path, required=True)
    validation.add_argument("--session")
    validation.add_argument("--price-run")
    validation.add_argument("--stage", choices=("review", "written"), default="written")
    init = commands.add_parser("init")
    init.add_argument("--workspace", type=Path, required=True)
    init.add_argument("--currency", default="EUR")
    migrate = commands.add_parser("migrate")
    migrate.add_argument("--workspace", type=Path, required=True)
    migrate.add_argument("--apply", metavar="REVIEWED_PLAN_ID")
    ensure = commands.add_parser("ensure-runtime")
    ensure.add_argument("--workspace", type=Path, required=True)
    ensure.add_argument("--extraction", action="store_true")
    tool = commands.add_parser("run")
    tool.add_argument("--workspace", type=Path, required=True)
    tool.add_argument("tool", choices=TOOLS)
    tool.add_argument("args", nargs=argparse.REMAINDER)
    arguments = parser.parse_args(argv)
    try:
        if arguments.action == "serve":
            from auto_bean.runtime import serve

            return serve()
        if arguments.action == "init":
            result = initialize(arguments.workspace, currency=arguments.currency)
        elif arguments.action == "migrate":
            result = (
                apply_migration(arguments.workspace, arguments.apply)
                if arguments.apply
                else plan_migration(arguments.workspace)
            )
        else:
            root = workspace(arguments.workspace)
            if arguments.action == "validate":
                args = [
                    "-m",
                    "auto_bean.reconciliation",
                    "--workspace",
                    str(root),
                    "--stage",
                    arguments.stage,
                ]
                if arguments.session:
                    args.extend(["--session", arguments.session])
                if arguments.price_run:
                    args.extend(["--price-run", arguments.price_run])
                return run_tool(root, "python", args)
            if arguments.action == "run":
                return run_tool(root, arguments.tool, arguments.args)
            result = {
                "status": "ok",
                "runtime": str(ensure_runtime(root, extraction=arguments.extraction)),
            }
    except (WorkflowError, OSError, ValueError) as error:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error_code": getattr(error, "code", "execution_error"),
                    "message": str(error),
                }
            ),
            file=sys.stderr if arguments.action == "serve" else sys.stdout,
        )
        return 1
    print(json.dumps(result, indent=2))
    return 2 if result.get("status") == "needs_input" else 0


if __name__ == "__main__":
    sys.exit(main())
