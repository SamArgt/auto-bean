from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from getpass import getpass
from pathlib import Path
from time import perf_counter

from auto_bean.checks import WorkspaceChecks
from auto_bean.environment import ToolProbe
from auto_bean.models import (
    CheckStatus,
    CommandOutcome,
    CurrentTaskReporter,
    DiagnosticCheck,
    ErrorCategory,
    InitContext,
    ProgressReporter,
    PromptResponder,
    UpdateContext,
)
from auto_bean.paths import (
    ProjectPaths,
    resolve_target_directory,
    resolve_workspace_directory,
)
from auto_bean.workspace_files import WorkspaceFileManager


@dataclass
class _WorkspaceWorkflowService:
    paths: ProjectPaths
    progress_reporter: ProgressReporter | None = None
    current_task_reporter: CurrentTaskReporter | None = None
    workspace_files: WorkspaceFileManager = field(default_factory=WorkspaceFileManager)
    checks: WorkspaceChecks = field(default_factory=WorkspaceChecks)

    def execution_error(
        self,
        workflow: str,
        *,
        details: dict[str, object],
        message: str = "Workflow execution failed unexpectedly.",
    ) -> CommandOutcome:
        return CommandOutcome(
            workflow=workflow,
            status="failed",
            error_code="execution_error",
            error_category=ErrorCategory.EXECUTION_ERROR,
            message=message,
            details=details,
        )

    def _record(self, checks: list[DiagnosticCheck], check: DiagnosticCheck) -> None:
        checks.append(check)
        if self.progress_reporter is not None:
            self.progress_reporter(check)

    def _run_check(
        self,
        *,
        checks: list[DiagnosticCheck],
        context: InitContext | UpdateContext,
        started: float,
        current_message: str,
        action: Callable[[], DiagnosticCheck],
        cleanup_target: Path | None = None,
        preserve_root: bool = True,
        extra_details: dict[str, object] | None = None,
        block_validation: bool = False,
    ) -> CommandOutcome | None:
        if self.current_task_reporter is not None:
            self.current_task_reporter(current_message)
        check_started = perf_counter()
        check = replace(action(), duration_seconds=perf_counter() - check_started)
        self._record(checks, check)
        if check.status is CheckStatus.FAIL:
            failure_details = dict(extra_details or {})
            if block_validation:
                failure_details["validation_status"] = "blocked"
            if cleanup_target is not None:
                self._cleanup_workspace(cleanup_target, preserve_root=preserve_root)
            return self._failure(
                checks=checks,
                context=context,
                started=started,
                check=check,
                extra_details=failure_details or None,
            )
        return None

    def _failure(
        self,
        *,
        checks: list[DiagnosticCheck],
        context: InitContext | UpdateContext,
        started: float,
        check: DiagnosticCheck,
        extra_details: dict[str, object] | None = None,
    ) -> CommandOutcome:
        details = context.as_details() | check.details
        if extra_details is not None:
            details |= extra_details
        return CommandOutcome(
            workflow="update" if isinstance(context, UpdateContext) else "init",
            status="failed",
            error_code=check.error_code,
            error_category=self._classify_error(check.error_code),
            message=check.message,
            details=details,
            checks=tuple(checks),
            duration_seconds=perf_counter() - started,
        )

    def _cleanup_workspace(
        self, target_directory: Path, *, preserve_root: bool
    ) -> None:
        if not target_directory.exists():
            return
        for relative_path in (
            ".git",
            ".gitignore",
            ".venv",
            ".codex",
            ".auto-bean",
            ".agents",
            "beancount",
            "docs",
            "scripts",
            "statements",
            "README.md",
            "AGENTS.md",
            "ledger.beancount",
        ):
            path = target_directory / relative_path
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            elif path.exists():
                path.unlink(missing_ok=True)
        if not preserve_root and not any(target_directory.iterdir()):
            target_directory.rmdir()

    def _classify_error(self, error_code: str | None) -> ErrorCategory | None:
        if error_code is None:
            return None
        if error_code in {
            "unsupported_environment",
            "missing_uv",
            "missing_git",
            "missing_template_assets",
            "missing_skill_sources",
            "missing_workspace",
            "missing_update_assets",
            "workspace_runtime_bootstrap_failed",
            "workspace_git_init_failed",
            "workspace_git_commit_failed",
        }:
            return ErrorCategory.PREREQUISITE_FAILURE
        if error_code in {
            "unsafe_project_name",
            "non_empty_target_directory",
            "non_directory_target_path",
            "not_auto_bean_workspace",
        }:
            return ErrorCategory.BLOCKED_UNSAFE_MUTATION
        if error_code in {
            "unsupported_coding_agent",
            "invalid_generated_ledger",
            "workspace_fava_unavailable",
            "workspace_docling_unavailable",
        }:
            return ErrorCategory.VALIDATION_FAILURE
        return ErrorCategory.EXECUTION_ERROR


@dataclass
class WorkspaceInitService(_WorkspaceWorkflowService):
    prompt: PromptResponder = input
    secret_prompt: PromptResponder = getpass

    def init(
        self,
        project_name: str,
        *,
        coding_agent: str | None = None,
        context7_api_key: str | None = None,
    ) -> CommandOutcome:
        started = perf_counter()
        target_directory, target_input_type = resolve_target_directory(
            self.paths, project_name
        )
        context = InitContext(
            project_name=project_name,
            target_input_type=target_input_type,
            working_directory=str(self.paths.working_directory),
            target_directory=str(target_directory),
            template_directory=str(self.paths.workspace_template_directory),
            skill_sources_directory=str(self.paths.skill_sources_directory),
        )
        checks: list[DiagnosticCheck] = []

        failure = self._run_check(
            checks=checks,
            context=context,
            started=started,
            current_message="Checking local environment",
            action=self.checks.check_environment,
        )
        if failure is not None:
            return failure
        failure = self._run_check(
            checks=checks,
            context=context,
            started=started,
            current_message="Validating target directory",
            action=lambda: self.checks.check_target(project_name, target_directory),
        )
        if failure is not None:
            return failure

        selected_agent = coding_agent or self.prompt_for_coding_agent()
        failure = self._run_check(
            checks=checks,
            context=context,
            started=started,
            current_message="Checking selected coding agent",
            action=lambda: self.checks.check_coding_agent(selected_agent),
        )
        if failure is not None:
            return failure
        failure = self._run_check(
            checks=checks,
            context=context,
            started=started,
            current_message="Checking workspace template assets",
            action=lambda: self.checks.check_required_assets(
                name="workspace_template_available",
                details_key="template_directory",
                error_code="missing_template_assets",
                message="Workspace template assets are available.",
                failure_message="Workspace template assets are missing.",
                root=Path(context.template_directory),
                required_paths=(
                    "README.md",
                    "ledger.beancount",
                    "AGENTS.md",
                    ".codex/config.toml",
                    "scripts/install-dependencies.sh",
                    "scripts/open-fava.sh",
                    "scripts/validate-ledger.sh",
                    ".auto-bean/memory/MEMORY.md",
                    "beancount/accounts.beancount",
                    "beancount/opening-balances.beancount",
                    ".auto-bean/memory/import_sources/.gitkeep",
                    ".auto-bean/artifacts/categorize/.gitkeep",
                    ".auto-bean/artifacts/import/.gitkeep",
                    "statements/parsed/.gitkeep",
                    "statements/import-status.yml",
                ),
            ),
        )
        if failure is not None:
            return failure
        failure = self._run_check(
            checks=checks,
            context=context,
            started=started,
            current_message="Checking authored skill assets",
            action=lambda: self.checks.check_required_assets(
                name="skill_sources_available",
                details_key="skill_sources_directory",
                error_code="missing_skill_sources",
                message="Authored skill source assets are available.",
                failure_message="Authored skill source assets are missing.",
                root=Path(context.skill_sources_directory),
                required_paths=(
                    "auto-bean-categorize/SKILL.md",
                    "auto-bean-query/SKILL.md",
                    "auto-bean-write/SKILL.md",
                    "auto-bean-import/SKILL.md",
                    "auto-bean-process/SKILL.md",
                    "auto-bean-memory/SKILL.md",
                ),
            ),
        )
        if failure is not None:
            return failure
        failure = self._run_check(
            checks=checks,
            context=context,
            started=started,
            current_message="Checking uv availability",
            action=lambda: self.checks.check_tool(
                "uv",
                name="uv_available",
                message="uv is available.",
                error_code="missing_uv",
                failure_message="The 'uv' command is required but was not found.",
                remediation=(
                    "Install uv, then run 'uv tool install --from . --force auto-bean'. Example: "
                    "https://docs.astral.sh/uv/getting-started/installation/"
                ),
            ),
        )
        if failure is not None:
            return failure
        selected_agent = "Codex"
        normalized_context7_api_key = self._normalize_context7_api_key(context7_api_key)

        target_preexisted = target_directory.exists()
        if self.current_task_reporter is not None:
            self.current_task_reporter("Copying workspace scaffold")
        scaffold_started = perf_counter()
        created_paths = self.workspace_files.scaffold_workspace(
            template_directory=Path(context.template_directory),
            skill_sources_directory=Path(context.skill_sources_directory),
            target_directory=target_directory,
            context7_api_key=normalized_context7_api_key,
        )
        blocked_details: dict[str, object] = {
            "coding_agent": selected_agent,
            "context7_mcp": "configured",
            "context7_api_key_status": (
                "stored" if normalized_context7_api_key else "not_provided"
            ),
            "created_paths": created_paths,
            "key_files": [
                ".codex/config.toml",
                "ledger.beancount",
                "AGENTS.md",
                ".agents/skills/auto-bean-categorize/SKILL.md",
                ".agents/skills/auto-bean-import/SKILL.md",
                ".agents/skills/auto-bean-process/SKILL.md",
                ".agents/skills/auto-bean-memory/SKILL.md",
                ".auto-bean/memory/MEMORY.md",
                ".auto-bean/memory/import_sources/.gitkeep",
                "statements/import-status.yml",
            ],
        }
        self._record(
            checks,
            DiagnosticCheck(
                name="workspace_scaffolded",
                status=CheckStatus.PASS,
                message="Workspace template copied successfully.",
                details={
                    "target_directory": str(target_directory),
                    "created_file_count": len(created_paths),
                },
                duration_seconds=perf_counter() - scaffold_started,
            ),
        )

        failure = self._run_check(
            checks=checks,
            context=context,
            started=started,
            current_message="Checking git availability",
            action=lambda: self.checks.check_tool(
                "git",
                name="workspace_git_available",
                message="git is available.",
                error_code="missing_git",
                failure_message="The 'git' command is required to initialize the workspace repository.",
                remediation=(
                    "Install Git, then rerun 'auto-bean init <PROJECT-NAME>' so the workspace "
                    "starts as a repository."
                ),
            ),
            cleanup_target=target_directory,
            preserve_root=target_preexisted,
            extra_details=blocked_details,
        )
        if failure is not None:
            return failure

        git_path = ToolProbe().find("git")
        assert git_path is not None
        failure = self._run_check(
            checks=checks,
            context=context,
            started=started,
            current_message="Initializing workspace git repository",
            action=lambda: self.checks.run_command_check(
                ["git", "init"],
                resolved_command=[git_path, "init"],
                cwd=target_directory,
                name="workspace_git_initialized",
                success_message="Workspace Git repository initialized.",
                error_code="workspace_git_init_failed",
                failure_message="Failed to initialize the workspace as a Git repository.",
                detail_key="git_command",
            ),
            cleanup_target=target_directory,
            preserve_root=target_preexisted,
            extra_details=blocked_details,
            block_validation=True,
        )
        if failure is not None:
            return failure
        failure = self._run_check(
            checks=checks,
            context=context,
            started=started,
            current_message="Bootstrapping workspace runtime",
            action=lambda: self.checks.bootstrap_workspace_runtime(target_directory),
            cleanup_target=target_directory,
            preserve_root=target_preexisted,
            extra_details=blocked_details,
            block_validation=True,
        )
        if failure is not None:
            return failure
        failure = self._run_check(
            checks=checks,
            context=context,
            started=started,
            current_message="Validating generated ledger",
            action=lambda: self.checks.validate_generated_ledger(target_directory),
            cleanup_target=target_directory,
            preserve_root=target_preexisted,
            extra_details=blocked_details,
        )
        if failure is not None:
            return failure
        failure = self._run_check(
            checks=checks,
            context=context,
            started=started,
            current_message="Checking Fava availability",
            action=lambda: self.checks.check_workspace_fava_available(target_directory),
            cleanup_target=target_directory,
            preserve_root=target_preexisted,
            extra_details=blocked_details,
        )
        if failure is not None:
            return failure
        failure = self._run_check(
            checks=checks,
            context=context,
            started=started,
            current_message="Checking Docling availability",
            action=lambda: self.checks.check_workspace_docling_available(
                target_directory
            ),
            cleanup_target=target_directory,
            preserve_root=target_preexisted,
            extra_details=blocked_details,
        )
        if failure is not None:
            return failure
        failure = self._run_check(
            checks=checks,
            context=context,
            started=started,
            current_message="Creating initial git commit",
            action=lambda: self.checks.create_initial_git_commit(
                target_directory, git_path
            ),
            cleanup_target=target_directory,
            preserve_root=target_preexisted,
            extra_details=blocked_details,
            block_validation=True,
        )
        if failure is not None:
            return failure

        validation_command = self.checks.bean_check_command(target_directory)
        details = (
            context.as_details()
            | blocked_details
            | {
                "coding_agent": selected_agent,
                "validation_command": " ".join(validation_command),
                "workspace_python": str(target_directory / ".venv" / "bin" / "python"),
                "workspace_bean_check": str(
                    target_directory / ".venv" / "bin" / "bean-check"
                ),
                "workspace_fava": str(target_directory / ".venv" / "bin" / "fava"),
                "workspace_docling": str(
                    target_directory / ".venv" / "bin" / "docling"
                ),
                "context7_mcp": "configured",
                "context7_api_key_status": (
                    "stored" if normalized_context7_api_key else "not_provided"
                ),
                "validation_status": "passed",
                "fava_status": "passed",
                "docling_status": "passed",
                "next_steps": [
                    f"cd {target_directory}",
                    "Review AGENTS.md for the Codex-first workspace workflow and path guide.",
                    "./scripts/validate-ledger.sh",
                    "./scripts/open-fava.sh",
                    "Use the installed .agents/skills/auto-bean-import/ workflow when you are ready to import statements.",
                ],
            }
        )
        return CommandOutcome(
            workflow="init",
            status="ok",
            error_code=None,
            error_category=None,
            message=f"Workspace created at {target_directory} and validated successfully.",
            details=details | checks[-2].details,
            checks=tuple(checks),
            duration_seconds=perf_counter() - started,
        )

    def prompt_for_coding_agent(self) -> str:
        response = self.prompt(
            "Which coding agent should this workspace target? [Codex]: "
        ).strip()
        return response or "Codex"

    def prompt_for_context7_api_key(self) -> str | None:
        response = self.secret_prompt(
            "Context7 API key [leave blank to skip]: "
        ).strip()
        return response or None

    def _normalize_context7_api_key(self, api_key: str | None) -> str | None:
        if api_key is None:
            return None
        normalized = api_key.strip()
        return normalized or None


@dataclass
class WorkspaceUpdateService(_WorkspaceWorkflowService):
    def update(self, workspace: str, *, check_only: bool = False) -> CommandOutcome:
        started = perf_counter()
        target_directory = resolve_workspace_directory(self.paths, workspace)
        context = UpdateContext(
            workspace_input=workspace,
            working_directory=str(self.paths.working_directory),
            target_directory=str(target_directory),
            template_directory=str(self.paths.workspace_template_directory),
            skill_sources_directory=str(self.paths.skill_sources_directory),
            check_only=check_only,
        )
        checks: list[DiagnosticCheck] = []

        for current_message, action in (
            (
                "Validating target workspace",
                lambda: self.checks.check_update_target(target_directory),
            ),
            (
                "Checking update assets",
                lambda: self.checks.check_update_assets(
                    Path(context.template_directory),
                    Path(context.skill_sources_directory),
                ),
            ),
        ):
            failure = self._run_check(
                checks=checks,
                context=context,
                started=started,
                current_message=current_message,
                action=action,
            )
            if failure is not None:
                return failure

        if self.current_task_reporter is not None:
            self.current_task_reporter("Comparing managed workspace files")
        compare_started = perf_counter()
        plan = self.workspace_files.planned_workspace_updates(
            target_directory=target_directory,
            template_directory=Path(context.template_directory),
            skill_sources_directory=Path(context.skill_sources_directory),
        )
        status = CheckStatus.WARN if plan else CheckStatus.PASS
        self._record(
            checks,
            DiagnosticCheck(
                name="managed_files_compared",
                status=status,
                message=(
                    "Managed workspace files differ from packaged assets."
                    if plan
                    else "Managed workspace files already match packaged assets."
                ),
                details=plan.as_details(),
                duration_seconds=perf_counter() - compare_started,
            ),
        )

        if check_only:
            return CommandOutcome(
                workflow="update",
                status="updates_available" if plan else "ok",
                error_code=None,
                error_category=None,
                message=(
                    f"{len(plan.changes)} managed workspace file(s) would be changed."
                    if plan
                    else "Managed workspace files are already up to date."
                ),
                details=context.as_details() | plan.as_details(),
                checks=tuple(checks),
                duration_seconds=perf_counter() - started,
                update_plan=plan,
            )

        if plan:
            if self.current_task_reporter is not None:
                self.current_task_reporter("Updating managed workspace files")
            update_started = perf_counter()
            self.workspace_files.apply_update_plan(
                target_directory=target_directory,
                plan=plan,
            )
            self._record(
                checks,
                DiagnosticCheck(
                    name="managed_files_updated",
                    status=CheckStatus.PASS,
                    message="Managed workspace files updated.",
                    details=plan.as_details()
                    | {
                        "updated_file_count": len(plan.updates),
                        "updated_paths": plan.update_paths,
                    },
                    duration_seconds=perf_counter() - update_started,
                ),
            )
        if not check_only:
            self.workspace_files.write_workspace_gitignore(target_directory)

        return CommandOutcome(
            workflow="update",
            status="ok",
            error_code=None,
            error_category=None,
            message=(
                f"Changed {len(plan.changes)} managed workspace file(s)."
                if plan
                else "Managed workspace files were already up to date."
            ),
            details=context.as_details()
            | plan.as_details()
            | {
                "updated_file_count": len(plan.updates),
                "updated_paths": plan.update_paths,
                "untouched_paths": [
                    "ledger.beancount",
                    "beancount/",
                    "statement/",
                    "statements/",
                    ".auto-bean/",
                ],
            },
            checks=tuple(checks),
            duration_seconds=perf_counter() - started,
            update_plan=plan,
        )


def build_workspace_init_service(start: Path | None = None) -> WorkspaceInitService:
    return WorkspaceInitService(paths=ProjectPaths(start=start))


def build_workspace_update_service(start: Path | None = None) -> WorkspaceUpdateService:
    return WorkspaceUpdateService(paths=ProjectPaths(start=start))


def build_init_service(start: Path | None = None) -> WorkspaceInitService:
    return build_workspace_init_service(start=start)
