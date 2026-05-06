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
from rich.syntax import Syntax

from auto_bean.init import (
    CheckStatus,
    CommandOutcome,
    DiagnosticCheck,
    WorkspaceFileChange,
    WorkspaceInitService,
    WorkspaceUpdateService,
    build_workspace_init_service,
    build_workspace_update_service,
)

_STATUS_STYLES = {
    CheckStatus.PASS: "green",
    CheckStatus.FAIL: "red",
    CheckStatus.WARN: "yellow",
}
_VERBOSE_CHECK_DETAIL_EXCLUSIONS = {"changes", "diffs"}


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> int:
    """Create and manage auto-bean ledger workspaces."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
    return 0


@cli.command(help="Create a new base Beancount ledger workspace.")
@click.argument("project_name")
@click.option(
    "--verbose",
    is_flag=True,
    help="Print stage results as they complete.",
)
def init(project_name: str, verbose: bool) -> int:
    service = build_workspace_init_service()
    coding_agent = service.prompt_for_coding_agent()
    context7_api_key = service.prompt_for_context7_api_key()
    renderer = RichWorkflowRenderer(verbose=verbose)
    result = _run_init(
        project_name=project_name,
        coding_agent=coding_agent,
        context7_api_key=context7_api_key,
        progress_reporter=renderer.report_check,
        current_task_reporter=renderer.start_check,
        service=service,
    )
    renderer.finish(result)
    return 0 if result.status == "ok" else 1


@cli.command(help="Update managed auto-bean skills and AGENTS.md in a workspace.")
@click.argument("workspace", required=False, default=".")
@click.option(
    "--check",
    "check_only",
    is_flag=True,
    help="Report managed file diffs without overwriting the workspace.",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Print stage results as they complete.",
)
def update(workspace: str, check_only: bool, verbose: bool) -> int:
    service = build_workspace_update_service()
    renderer = RichWorkflowRenderer(verbose=verbose, description="Updating workspace")
    result = _run_update(
        workspace=workspace,
        check_only=check_only,
        progress_reporter=renderer.report_check,
        current_task_reporter=renderer.start_check,
        service=service,
    )
    renderer.finish_update(result, check_only=check_only)
    return 1 if result.status not in {"ok"} else 0


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


def _run_init(
    *,
    project_name: str,
    coding_agent: str | None = None,
    context7_api_key: str | None = None,
    progress_reporter: Callable[[DiagnosticCheck], None] | None = None,
    current_task_reporter: Callable[[str], None] | None = None,
    service: WorkspaceInitService | None = None,
) -> CommandOutcome:
    init_service = service if service is not None else build_workspace_init_service()
    try:
        init_service.progress_reporter = progress_reporter
        init_service.current_task_reporter = current_task_reporter
        return init_service.init(
            project_name,
            coding_agent=coding_agent,
            context7_api_key=context7_api_key,
        )
    except Exception as exc:
        return init_service.execution_error(
            "init",
            details={
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
            },
        )


def _run_update(
    *,
    workspace: str,
    check_only: bool = False,
    progress_reporter: Callable[[DiagnosticCheck], None] | None = None,
    current_task_reporter: Callable[[str], None] | None = None,
    service: WorkspaceUpdateService | None = None,
) -> CommandOutcome:
    update_service = (
        service if service is not None else build_workspace_update_service()
    )
    try:
        update_service.progress_reporter = progress_reporter
        update_service.current_task_reporter = current_task_reporter
        return update_service.update(workspace, check_only=check_only)
    except Exception as exc:
        return update_service.execution_error(
            "update",
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
    def __init__(
        self,
        *,
        verbose: bool,
        description: str = "Initializing workspace",
        console: Console | None = None,
    ) -> None:
        self.verbose = verbose
        self.console = console if console is not None else Console()
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed} checks"),
            TimeElapsedColumn(),
            console=self.console,
            transient=True,
        )
        self._task_id = self.progress.add_task(description, total=None)
        self.progress.start()

    def start_check(self, message: str) -> None:
        self.progress.update(self._task_id, description=message)

    def report_check(self, check: DiagnosticCheck) -> None:
        self.progress.update(self._task_id, advance=1)
        if not self.verbose:
            return
        status_label = check.status.value.upper()
        status_style = _STATUS_STYLES[check.status]
        duration_text = f"{check.duration_seconds:.3f}s"
        self.progress.console.print(
            f"[{status_style}][{status_label}][/{status_style}] {check.name}: {check.message} [dim]({duration_text})[/dim]"
        )
        for key, value in check.details.items():
            if value and key not in _VERBOSE_CHECK_DETAIL_EXCLUSIONS:
                self.progress.console.print(f"  [dim]{key}:[/dim] {value}")

    def finish(self, result: CommandOutcome) -> None:
        self.progress.update(self._task_id, completed=len(result.checks))
        self.progress.stop()
        style = "green" if result.status == "ok" else "red"
        label = "Success" if result.status == "ok" else "Needs update"
        if result.status not in {"ok", "updates_available"}:
            label = "Failed"
        self.console.print(f"[bold {style}]{label}:[/bold {style}] {result.message}")

    def finish_update(self, result: CommandOutcome, *, check_only: bool) -> None:
        self.progress.update(self._task_id, completed=len(result.checks))
        self.progress.stop()
        if result.status == "ok":
            style = "green"
            label = "Success"
        elif result.status == "updates_available":
            style = "yellow"
            label = "Needs update"
        else:
            style = "red"
            label = "Failed"
        self.console.print(f"[bold {style}]{label}:[/bold {style}] {result.message}")
        if result.status not in {"ok", "updates_available"}:
            return
        plan = result.update_plan
        if plan is None or not plan:
            return
        update_label = "Would update" if check_only else "Updated"
        delete_label = "Would delete" if check_only else "Deleted"
        if plan.updates:
            update_lines = sum(change.concerned_line_count for change in plan.updates)
            self.console.print(
                f"[bold green]{update_label} {len(plan.updates)} file(s), "
                f"{update_lines} line(s):[/bold green]"
            )
            for change in plan.updates:
                self.console.print(
                    f"  [dim]{change.path}[/dim] "
                    f"({change.concerned_line_count} lines, "
                    f"[green]+{change.added_line_count}[/green]/"
                    f"[red]-{change.removed_line_count}[/red])"
                )
        if plan.removals:
            self.console.print(
                f"[bold red]{delete_label} {len(plan.removals)} file(s):[/bold red]"
            )
            for change in plan.removals:
                self.console.print(f"  [dim]{change.path}[/dim]")
        if self.verbose:
            self._render_update_diffs(plan.changes)

    def _render_update_diffs(self, changes: Sequence[WorkspaceFileChange]) -> None:
        for change in changes:
            if not change.diff:
                continue
            self.console.print()
            self.console.print(
                f"[bold]diff --git a/{change.path} b/{change.path}[/bold]"
            )
            self.console.print(
                Syntax(
                    change.diff.rstrip(),
                    "diff",
                    background_color="default",
                    word_wrap=False,
                )
            )
