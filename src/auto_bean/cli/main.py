from __future__ import annotations

import json
from collections.abc import Callable, Sequence

import click
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from auto_bean.application.setup import SetupService, build_setup_service
from auto_bean.domain.setup import CheckStatus, CommandOutcome, DiagnosticCheck

_INIT_STAGE_TOTAL = 11
_STATUS_STYLES = {
    CheckStatus.PASS: "green",
    CheckStatus.FAIL: "red",
    CheckStatus.WARN: "yellow",
}


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
@click.option(
    "--verbose",
    is_flag=True,
    help="Print stage results as they complete.",
)
def init(project_name: str, as_json: bool, verbose: bool) -> int:
    service = build_setup_service()

    if as_json:
        result = _run_workflow("init", project_name=project_name, service=service)
        render_result(result, as_json=True, verbose=verbose)
        return 0 if result.status == "ok" else 1

    coding_agent = service.prompt_for_coding_agent()
    renderer = RichWorkflowRenderer(verbose=verbose)
    result = _run_workflow(
        "init",
        project_name=project_name,
        coding_agent=coding_agent,
        progress_reporter=renderer.report_check,
        service=service,
    )
    renderer.finish(result)
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


def _run_workflow(
    workflow: str,
    *,
    project_name: str,
    coding_agent: str | None = None,
    progress_reporter: Callable[[DiagnosticCheck], None] | None = None,
    service: SetupService | None = None,
) -> CommandOutcome:
    try:
        setup_service = service if service is not None else build_setup_service()
        setup_service.progress_reporter = progress_reporter
        if workflow == "init":
            return setup_service.init(project_name, coding_agent=coding_agent)
        return setup_service.execution_error(
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


def render_result(result: CommandOutcome, *, as_json: bool, verbose: bool) -> None:
    if as_json:
        click.echo(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return

    renderer = RichWorkflowRenderer(verbose=verbose)
    for check in result.checks:
        renderer.report_check(check)
    renderer.finish(result)


class RichWorkflowRenderer:
    def __init__(self, *, verbose: bool) -> None:
        self.verbose = verbose
        self.console = Console()
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            console=self.console,
            transient=True,
        )
        self._task_id = self.progress.add_task(
            "Initializing workspace", total=_INIT_STAGE_TOTAL
        )
        self.progress.start()

    def report_check(self, check: DiagnosticCheck) -> None:
        self.progress.update(self._task_id, advance=1, description=check.message)
        if not self.verbose:
            return
        status_label = check.status.value.upper()
        status_style = _STATUS_STYLES[check.status]
        self.progress.console.print(
            f"[{status_style}][{status_label}][/{status_style}] {check.name}: {check.message}"
        )
        for key, value in check.details.items():
            if value:
                self.progress.console.print(f"  [dim]{key}:[/dim] {value}")

    def finish(self, result: CommandOutcome) -> None:
        if not self.progress.finished:
            self.progress.update(self._task_id, completed=len(result.checks))
        self.progress.stop()
        style = "green" if result.status == "ok" else "red"
        label = "Success" if result.status == "ok" else "Failed"
        self.console.print(f"[bold {style}]{label}:[/bold {style}] {result.message}")
