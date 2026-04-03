from __future__ import annotations

import json
from collections.abc import Sequence

import click

from auto_bean.application.setup import build_setup_service
from auto_bean.domain.setup import CheckStatus, CommandOutcome


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> int:
    """Create and manage auto-bean ledger workspaces."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
    return 0


@cli.command(help="Create a new base Beancount ledger workspace.")
@click.argument("project_name")
@click.option("--json", "as_json", is_flag=True, help="Render the result as JSON.")
def init(project_name: str, as_json: bool) -> int:
    result = _run_workflow("init", project_name=project_name)
    render_result(result, as_json=as_json)
    return 0 if result.status == "ok" else 1


def main(argv: Sequence[str] | None = None) -> int:
    try:
        result = cli.main(
            args=list(argv) if argv is not None else None,
            prog_name="auto-bean",
            standalone_mode=False,
        )
    except click.ClickException as exc:
        exc.show()
        return exc.exit_code
    except click.exceptions.Exit as exc:
        return exc.exit_code
    return int(result or 0)


def _run_workflow(workflow: str, *, project_name: str) -> CommandOutcome:
    try:
        service = build_setup_service()
        if workflow == "init":
            return service.init(project_name)
        return service.execution_error(
            workflow,
            details={"unsupported_command": workflow},
            message="Unsupported command.",
        )
    except Exception as exc:
        return build_setup_service().execution_error(
            workflow,
            details={
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
            },
        )


def render_result(result: CommandOutcome, *, as_json: bool) -> None:
    if as_json:
        click.echo(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return

    if result.workflow == "init":
        click.echo("auto-bean init")
    click.echo(f"workflow: {result.workflow}")
    click.echo(f"status: {result.status}")
    if result.error_code:
        click.echo(f"error_code: {result.error_code}")
    if result.error_category:
        click.echo(f"error_category: {result.error_category.value}")
    click.echo(f"message: {result.message}")
    click.echo(f"duration_seconds: {result.duration_seconds:.3f}")
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
    click.echo(f"[{indicator}] {diagnostic.name}: {diagnostic.message}")
    for key, value in diagnostic.details.items():
        if value:
            click.echo(f"  - {key}: {value}")


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
            click.echo(f"{key}: {value}")

    for key in ("created_paths", "next_steps", "key_files"):
        value = details.get(key)
        if isinstance(value, list) and value:
            click.echo(f"{key}:")
            for item in value:
                click.echo(f"  - {item}")
