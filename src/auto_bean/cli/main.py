from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from auto_bean.application.setup import build_setup_service
from auto_bean.domain.setup import CheckStatus, CommandOutcome


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="auto-bean",
        description="Create and manage auto-bean ledger workspaces.",
    )
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser(
        "init",
        help="Create a new base Beancount ledger workspace.",
    )
    init_parser.add_argument("project_name", help="Name of the workspace to create.")
    init_parser.add_argument(
        "--json",
        action="store_true",
        help="Render the result as JSON.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    try:
        service = build_setup_service()
        if args.command == "init":
            result = service.init(args.project_name)
        else:
            result = service.execution_error(
                args.command,
                details={"unsupported_command": args.command},
                message="Unsupported command.",
            )
    except Exception as exc:
        result = build_setup_service().execution_error(
            args.command or "unknown",
            details={
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
            },
        )
    render_result(result, as_json=args.json)
    return 0 if result.status == "ok" else 1


def render_result(result: CommandOutcome, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return

    if result.workflow == "init":
        print("auto-bean init")
    print(f"workflow: {result.workflow}")
    print(f"status: {result.status}")
    if result.error_code:
        print(f"error_code: {result.error_code}")
    if result.error_category:
        print(f"error_category: {result.error_category.value}")
    print(f"message: {result.message}")
    print(f"duration_seconds: {result.duration_seconds:.3f}")
    _render_detail_lines(result.details)
    for check in result.checks:
        _render_check(check)


def _render_check(check: object) -> None:
    from auto_bean.domain.setup import DiagnosticCheck

    diagnostic = check if isinstance(check, DiagnosticCheck) else None
    if diagnostic is None:
        return
    indicator = {
        CheckStatus.PASS: "PASS",
        CheckStatus.FAIL: "FAIL",
        CheckStatus.WARN: "WARN",
    }[diagnostic.status]
    print(f"[{indicator}] {diagnostic.name}: {diagnostic.message}")
    for key, value in diagnostic.details.items():
        if value:
            print(f"  - {key}: {value}")


def _render_detail_lines(details: dict[str, object]) -> None:
    scalar_keys = (
        "project_name",
        "target_input_type",
        "working_directory",
        "target_directory",
        "template_directory",
        "skill_sources_directory",
        "coding_agent",
        "validation_command",
        "validation_status",
    )
    for key in scalar_keys:
        value = details.get(key)
        if value:
            print(f"{key}: {value}")

    for key in ("created_paths", "next_steps", "key_files"):
        value = details.get(key)
        if isinstance(value, list) and value:
            print(f"{key}:")
            for item in value:
                print(f"  - {item}")
