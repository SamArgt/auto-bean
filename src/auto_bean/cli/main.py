from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from auto_bean.application.setup import build_setup_service
from auto_bean.domain.setup import CheckStatus, WorkflowResult


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="auto-bean",
        description="Bootstrap and verify the local auto-bean development environment.",
    )
    subparsers = parser.add_subparsers(dest="command")

    bootstrap_parser = subparsers.add_parser(
        "bootstrap",
        help="Install or verify the repo-local environment and required dependencies.",
    )
    bootstrap_parser.add_argument(
        "--json",
        action="store_true",
        help="Render the result as JSON.",
    )

    readiness_parser = subparsers.add_parser(
        "readiness",
        help="Verify that the current repo-local environment is ready for later workflows.",
    )
    readiness_parser.add_argument(
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

    service = build_setup_service()
    result = service.bootstrap() if args.command == "bootstrap" else service.readiness()
    render_result(result, as_json=args.json)
    return 0 if result.status == "ok" else 1


def render_result(result: WorkflowResult, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return

    print(f"status: {result.status}")
    if result.error_code:
        print(f"error_code: {result.error_code}")
    print(f"message: {result.message}")
    print(f"duration_seconds: {result.duration_seconds:.3f}")
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
