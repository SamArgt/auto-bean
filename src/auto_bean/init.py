from __future__ import annotations

import platform
import re
import shutil
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from difflib import unified_diff
from enum import Enum
from pathlib import Path
from stat import S_IEXEC
from time import perf_counter
from typing import Protocol


class CheckStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"


class ErrorCategory(str, Enum):
    VALIDATION_FAILURE = "validation_failure"
    BLOCKED_UNSAFE_MUTATION = "blocked_unsafe_mutation"
    PREREQUISITE_FAILURE = "prerequisite_failure"
    EXECUTION_ERROR = "execution_error"


@dataclass(frozen=True)
class DiagnosticCheck:
    name: str
    status: CheckStatus
    message: str
    error_code: str | None = None
    details: dict[str, object] = field(default_factory=dict)
    duration_seconds: float = 0.0

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "status": self.status.value,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "duration_seconds": round(self.duration_seconds, 3),
        }


@dataclass(frozen=True)
class CommandOutcome:
    workflow: str
    status: str
    error_code: str | None
    error_category: ErrorCategory | None = None
    message: str = ""
    details: dict[str, object] = field(default_factory=dict)
    checks: tuple[DiagnosticCheck, ...] = ()
    duration_seconds: float = 0.0

    def as_dict(self) -> dict[str, object]:
        return {
            "workflow": self.workflow,
            "status": self.status,
            "error_code": self.error_code,
            "error_category": self.error_category.value
            if self.error_category is not None
            else None,
            "message": self.message,
            "details": self.details,
            "checks": [check.as_dict() for check in self.checks],
            "duration_seconds": round(self.duration_seconds, 3),
        }


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class EnvironmentInfo:
    system: str
    release: str
    machine: str
    python_version: str


class PlatformInspector(Protocol):
    def inspect(self) -> EnvironmentInfo: ...


class ToolLocator(Protocol):
    def find(self, command: str) -> str | None: ...


class CommandExecutor(Protocol):
    def run(self, args: Sequence[str], cwd: Path | None = None) -> CommandResult: ...


type PromptResponder = Callable[[str], str]
type ProgressReporter = Callable[[DiagnosticCheck], None]
type CurrentTaskReporter = Callable[[str], None]


class PlatformProbe:
    def inspect(self) -> EnvironmentInfo:
        return EnvironmentInfo(
            system=platform.system(),
            release=platform.release(),
            machine=platform.machine(),
            python_version=platform.python_version(),
        )


class ToolProbe:
    def find(self, command: str) -> str | None:
        return shutil.which(command)


class CommandRunner:
    def run(self, args: Sequence[str], cwd: Path | None = None) -> CommandResult:
        completed = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        return CommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout.strip(),
            stderr=completed.stderr.strip(),
        )


class ProjectPaths:
    def __init__(self, start: Path | None = None) -> None:
        self._start = (start or Path.cwd()).resolve()

    @property
    def working_directory(self) -> Path:
        return self._start

    @property
    def repo_root(self) -> Path:
        for candidate in (self._start, *self._start.parents):
            if (candidate / "pyproject.toml").is_file() and (
                candidate / "src"
            ).is_dir():
                return candidate
        msg = "Unable to locate the project root from the current working directory."
        raise RuntimeError(msg)

    @property
    def installed_resources_directory(self) -> Path:
        return Path(__file__).resolve().parent / "_packaged_assets"

    @property
    def source_checkout_resources_directory(self) -> Path:
        module_path = Path(__file__).resolve()
        for parent in module_path.parents:
            if (parent / "workspace_template").is_dir() and (
                parent / "skill_sources"
            ).is_dir():
                return parent
        return module_path.parent

    @property
    def resource_roots(self) -> tuple[Path, ...]:
        roots: list[Path] = []
        for candidate in (
            self.installed_resources_directory,
            self.source_checkout_resources_directory,
        ):
            if candidate not in roots:
                roots.append(candidate)
        return tuple(roots)

    @property
    def workspace_template_directory(self) -> Path:
        return self._resolve_resource_directory("workspace_template")

    @property
    def skill_sources_directory(self) -> Path:
        return self._resolve_resource_directory("skill_sources")

    def _resolve_resource_directory(self, name: str) -> Path:
        candidates: list[Path] = []
        try:
            candidates.append(self.repo_root / name)
        except RuntimeError:
            pass
        candidates.extend(root / name for root in self.resource_roots)
        for candidate in candidates:
            if candidate.is_dir():
                return candidate
        return candidates[0] if candidates else Path(name)


@dataclass(frozen=True)
class InitContext:
    project_name: str
    target_input_type: str
    working_directory: str
    target_directory: str
    template_directory: str
    skill_sources_directory: str

    def as_details(self) -> dict[str, object]:
        return {
            "project_name": self.project_name,
            "target_input_type": self.target_input_type,
            "working_directory": self.working_directory,
            "target_directory": self.target_directory,
            "template_directory": self.template_directory,
            "skill_sources_directory": self.skill_sources_directory,
        }


@dataclass(frozen=True)
class UpdateContext:
    workspace_input: str
    working_directory: str
    target_directory: str
    template_directory: str
    skill_sources_directory: str
    check_only: bool

    def as_details(self) -> dict[str, object]:
        return {
            "workspace_input": self.workspace_input,
            "working_directory": self.working_directory,
            "target_directory": self.target_directory,
            "template_directory": self.template_directory,
            "skill_sources_directory": self.skill_sources_directory,
            "check_only": self.check_only,
        }


@dataclass
class InitService:
    paths: ProjectPaths
    platform: PlatformInspector
    tools: ToolLocator
    commands: CommandExecutor
    prompt: PromptResponder = input
    progress_reporter: ProgressReporter | None = None
    current_task_reporter: CurrentTaskReporter | None = None

    def init(
        self, project_name: str, *, coding_agent: str | None = None
    ) -> CommandOutcome:
        started = perf_counter()
        target_directory, target_input_type = self._resolve_target_directory(
            project_name
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

        # Stage 1: validate the local environment and requested target before we
        # create or modify anything on disk.
        failure = self._run_check(
            checks=checks,
            context=context,
            started=started,
            current_message="Checking local environment",
            action=self._check_environment,
        )
        if failure is not None:
            return failure
        failure = self._run_check(
            checks=checks,
            context=context,
            started=started,
            current_message="Validating target directory",
            action=lambda: self._check_target(project_name, target_directory),
        )
        if failure is not None:
            return failure

        # Stage 2: confirm the scaffold inputs are present and compatible with
        # the current workspace configuration.
        selected_agent = coding_agent or self.prompt_for_coding_agent()
        failure = self._run_check(
            checks=checks,
            context=context,
            started=started,
            current_message="Checking selected coding agent",
            action=lambda: self._check_coding_agent(selected_agent),
        )
        if failure is not None:
            return failure
        failure = self._run_check(
            checks=checks,
            context=context,
            started=started,
            current_message="Checking workspace template assets",
            action=lambda: self._check_required_assets(
                name="workspace_template_available",
                details_key="template_directory",
                error_code="missing_template_assets",
                message="Workspace template assets are available.",
                failure_message="Workspace template assets are missing.",
                root=Path(context.template_directory),
                required_paths=(
                    "ledger.beancount",
                    "AGENTS.md",
                    "beancount/accounts.beancount",
                    "beancount/opening-balances.beancount",
                    ".auto-bean/memory/account_mappings.json",
                    ".auto-bean/memory/category_mappings.json",
                    ".auto-bean/memory/clarification_outcomes.json",
                    ".auto-bean/memory/deduplication_decisions.json",
                    ".auto-bean/memory/import_sources/.gitkeep",
                    ".auto-bean/memory/import_sources/index.json",
                    ".auto-bean/memory/naming_conventions.json",
                    ".auto-bean/memory/transfer_detection.json",
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
            action=lambda: self._check_required_assets(
                name="skill_sources_available",
                details_key="skill_sources_directory",
                error_code="missing_skill_sources",
                message="Authored skill source assets are available.",
                failure_message="Authored skill source assets are missing.",
                root=Path(context.skill_sources_directory),
                required_paths=(
                    "auto-bean-apply/SKILL.md",
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
            action=lambda: self._check_tool(
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

        # Stage 3: materialize the workspace scaffold so the remaining steps can
        # operate on a concrete repository.
        target_preexisted = target_directory.exists()
        if self.current_task_reporter is not None:
            self.current_task_reporter("Copying workspace scaffold")
        scaffold_started = perf_counter()
        created_paths = self._scaffold_workspace(
            context=context, target_directory=target_directory
        )
        blocked_details: dict[str, object] = {
            "coding_agent": selected_agent,
            "created_paths": created_paths,
            "key_files": [
                "ledger.beancount",
                "AGENTS.md",
                ".agents/skills/auto-bean-apply/SKILL.md",
                ".agents/skills/auto-bean-import/SKILL.md",
                ".agents/skills/auto-bean-process/SKILL.md",
                ".agents/skills/auto-bean-memory/SKILL.md",
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

        # Stage 4: initialize git and the local runtime, then verify the new
        # workspace is runnable before we keep it.
        failure = self._run_check(
            checks=checks,
            context=context,
            started=started,
            current_message="Checking git availability",
            action=lambda: self._check_tool(
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

        git_path = self.tools.find("git")
        assert git_path is not None
        failure = self._run_check(
            checks=checks,
            context=context,
            started=started,
            current_message="Initializing workspace git repository",
            action=lambda: self._run_command_check(
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
            action=lambda: self._bootstrap_workspace_runtime(target_directory),
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
            action=lambda: self._validate_generated_ledger(target_directory),
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
            action=lambda: self._check_workspace_fava_available(target_directory),
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
            action=lambda: self._check_workspace_docling_available(target_directory),
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
            action=lambda: self._create_initial_git_commit(target_directory, git_path),
            cleanup_target=target_directory,
            preserve_root=target_preexisted,
            extra_details=blocked_details,
            block_validation=True,
        )
        if failure is not None:
            return failure

        # Stage 5: assemble the user-facing result payload once the scaffold has
        # passed validation and the workspace is ready to use.
        validation_command = self._bean_check_command(target_directory)
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

    def update(self, workspace: str, *, check_only: bool = False) -> CommandOutcome:
        started = perf_counter()
        target_directory = self._resolve_workspace_directory(workspace)
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
                lambda: self._check_update_target(target_directory),
            ),
            (
                "Checking update assets",
                lambda: self._check_update_assets(
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
        changes = self._planned_workspace_updates(
            target_directory=target_directory,
            template_directory=Path(context.template_directory),
            skill_sources_directory=Path(context.skill_sources_directory),
        )
        changed_paths = [str(change["path"]) for change in changes]
        status = CheckStatus.WARN if changes else CheckStatus.PASS
        self._record(
            checks,
            DiagnosticCheck(
                name="managed_files_compared",
                status=status,
                message=(
                    "Managed workspace files differ from packaged assets."
                    if changes
                    else "Managed workspace files already match packaged assets."
                ),
                details={
                    "changed_file_count": len(changes),
                    "changed_paths": changed_paths,
                    "diffs": {
                        str(change["path"]): change["diff"] for change in changes
                    },
                },
                duration_seconds=perf_counter() - compare_started,
            ),
        )

        if check_only:
            return CommandOutcome(
                workflow="update",
                status="updates_available" if changes else "ok",
                error_code=None,
                error_category=None,
                message=(
                    f"{len(changes)} managed workspace file(s) would be updated."
                    if changes
                    else "Managed workspace files are already up to date."
                ),
                details=context.as_details()
                | {
                    "changed_file_count": len(changes),
                    "changed_paths": changed_paths,
                    "diffs": {
                        str(change["path"]): change["diff"] for change in changes
                    },
                },
                checks=tuple(checks),
                duration_seconds=perf_counter() - started,
            )

        if changes:
            if self.current_task_reporter is not None:
                self.current_task_reporter("Updating managed workspace files")
            update_started = perf_counter()
            for change in changes:
                source_path = Path(str(change["source_path"]))
                target_path = target_directory / str(change["path"])
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, target_path)
            self._record(
                checks,
                DiagnosticCheck(
                    name="managed_files_updated",
                    status=CheckStatus.PASS,
                    message="Managed workspace files updated.",
                    details={
                        "updated_file_count": len(changes),
                        "updated_paths": changed_paths,
                    },
                    duration_seconds=perf_counter() - update_started,
                ),
            )

        return CommandOutcome(
            workflow="update",
            status="ok",
            error_code=None,
            error_category=None,
            message=(
                f"Updated {len(changes)} managed workspace file(s)."
                if changes
                else "Managed workspace files were already up to date."
            ),
            details=context.as_details()
            | {
                "updated_file_count": len(changes),
                "updated_paths": changed_paths,
                "untouched_paths": [
                    "ledger.beancount",
                    "beancount/",
                    ".auto-bean/",
                ],
            },
            checks=tuple(checks),
            duration_seconds=perf_counter() - started,
        )

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

    def prompt_for_coding_agent(self) -> str:
        response = self.prompt(
            "Which coding agent should this workspace target? [Codex]: "
        ).strip()
        return response or "Codex"

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

    def _scaffold_workspace(
        self, *, context: InitContext, target_directory: Path
    ) -> list[str]:
        target_directory.mkdir(parents=True, exist_ok=True)
        created_paths = self._copy_tree(
            source=Path(context.template_directory),
            destination=target_directory,
        )
        created_paths.extend(
            self._copy_tree(
                source=Path(context.skill_sources_directory),
                destination=target_directory / ".agents" / "skills",
                prefix=".agents/skills",
            )
        )
        created_paths.extend(self._write_workspace_scripts(target_directory))
        return created_paths

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

    def _resolve_target_directory(self, project_name: str) -> tuple[Path, str]:
        if looks_like_path(project_name):
            return (
                (
                    self.paths.working_directory / Path(project_name).expanduser()
                ).resolve(),
                "path",
            )

        try:
            repo_root = self.paths.repo_root
        except RuntimeError:
            return ((self.paths.working_directory / project_name).resolve(), "name")

        if (
            self.paths.working_directory == repo_root
            or repo_root in self.paths.working_directory.parents
        ):
            return ((repo_root.parent / project_name).resolve(), "name")
        return ((self.paths.working_directory / project_name).resolve(), "name")

    def _resolve_workspace_directory(self, workspace: str) -> Path:
        path = Path(workspace).expanduser()
        if path.is_absolute():
            return path.resolve()
        return (self.paths.working_directory / path).resolve()

    def _check_environment(self) -> DiagnosticCheck:
        environment = self.platform.inspect()
        if environment.system != "Darwin":
            return DiagnosticCheck(
                name="supported_environment",
                status=CheckStatus.FAIL,
                error_code="unsupported_environment",
                message="auto-bean currently supports macOS only.",
                details={
                    "detected_system": environment.system,
                    "detected_release": environment.release,
                    "detected_machine": environment.machine,
                    "remediation": "Run this workflow on a supported macOS machine.",
                },
            )
        return DiagnosticCheck(
            name="supported_environment",
            status=CheckStatus.PASS,
            message="Supported macOS environment detected.",
            details={
                "detected_system": environment.system,
                "detected_release": environment.release,
                "detected_machine": environment.machine,
                "python_version": environment.python_version,
            },
        )

    def _check_target(
        self, project_name: str, target_directory: Path
    ) -> DiagnosticCheck:
        if looks_like_path(project_name):
            if project_name.strip() in {"", ".", ".."}:
                return DiagnosticCheck(
                    name="project_name_valid",
                    status=CheckStatus.FAIL,
                    error_code="unsafe_project_name",
                    message="Target path must point to a workspace directory, not '.' or '..'.",
                    details={
                        "project_name": project_name,
                        "target_directory": str(target_directory),
                    },
                )
        elif not sanitize_project_name(project_name):
            return DiagnosticCheck(
                name="project_name_valid",
                status=CheckStatus.FAIL,
                error_code="unsafe_project_name",
                message="Project name is unsafe. Use letters, numbers, dots, underscores, or dashes only, or pass a relative/absolute path.",
                details={
                    "project_name": project_name,
                    "target_directory": str(target_directory),
                },
            )
        if target_directory.exists() and not target_directory.is_dir():
            return DiagnosticCheck(
                name="project_name_valid",
                status=CheckStatus.FAIL,
                error_code="non_directory_target_path",
                message="Target path already exists and is not a directory.",
                details={
                    "project_name": project_name,
                    "target_directory": str(target_directory),
                },
            )
        if target_directory.exists() and any(target_directory.iterdir()):
            return DiagnosticCheck(
                name="project_name_valid",
                status=CheckStatus.FAIL,
                error_code="non_empty_target_directory",
                message="Target directory already exists and is not empty.",
                details={
                    "project_name": project_name,
                    "target_directory": str(target_directory),
                },
            )
        return DiagnosticCheck(
            name="project_name_valid",
            status=CheckStatus.PASS,
            message="Target directory is valid.",
            details={
                "project_name": project_name,
                "target_directory": str(target_directory),
            },
        )

    def _check_update_target(self, target_directory: Path) -> DiagnosticCheck:
        if not target_directory.exists():
            return DiagnosticCheck(
                name="workspace_target_valid",
                status=CheckStatus.FAIL,
                error_code="missing_workspace",
                message="Target workspace does not exist.",
                details={"target_directory": str(target_directory)},
            )
        if not target_directory.is_dir():
            return DiagnosticCheck(
                name="workspace_target_valid",
                status=CheckStatus.FAIL,
                error_code="non_directory_target_path",
                message="Target path is not a directory.",
                details={"target_directory": str(target_directory)},
            )
        missing_markers = [
            path
            for path in ("AGENTS.md", ".agents/skills")
            if not (target_directory / path).exists()
        ]
        if missing_markers:
            return DiagnosticCheck(
                name="workspace_target_valid",
                status=CheckStatus.FAIL,
                error_code="not_auto_bean_workspace",
                message="Target path does not look like an auto-bean workspace.",
                details={
                    "target_directory": str(target_directory),
                    "missing_markers": ", ".join(missing_markers),
                },
            )
        return DiagnosticCheck(
            name="workspace_target_valid",
            status=CheckStatus.PASS,
            message="Target workspace is valid.",
            details={"target_directory": str(target_directory)},
        )

    def _check_update_assets(
        self, template_directory: Path, skill_sources_directory: Path
    ) -> DiagnosticCheck:
        missing = [
            str(path)
            for path in (
                template_directory / "AGENTS.md",
                skill_sources_directory / "auto-bean-apply" / "SKILL.md",
                skill_sources_directory / "auto-bean-query" / "SKILL.md",
                skill_sources_directory / "auto-bean-write" / "SKILL.md",
                skill_sources_directory / "auto-bean-import" / "SKILL.md",
                skill_sources_directory / "auto-bean-process" / "SKILL.md",
                skill_sources_directory / "auto-bean-memory" / "SKILL.md",
            )
            if not path.exists()
        ]
        if missing:
            return DiagnosticCheck(
                name="update_assets_available",
                status=CheckStatus.FAIL,
                error_code="missing_update_assets",
                message="Packaged update assets are missing.",
                details={"missing_assets": ", ".join(missing)},
            )
        return DiagnosticCheck(
            name="update_assets_available",
            status=CheckStatus.PASS,
            message="Packaged update assets are available.",
            details={
                "template_directory": str(template_directory),
                "skill_sources_directory": str(skill_sources_directory),
            },
        )

    def _check_coding_agent(self, coding_agent: str) -> DiagnosticCheck:
        if coding_agent.casefold() != "codex":
            return DiagnosticCheck(
                name="coding_agent_selected",
                status=CheckStatus.FAIL,
                error_code="unsupported_coding_agent",
                message="Only the Codex coding agent is supported right now.",
                details={
                    "coding_agent": coding_agent,
                    "supported_agents": "Codex",
                },
            )
        return DiagnosticCheck(
            name="coding_agent_selected",
            status=CheckStatus.PASS,
            message="Coding agent selected.",
            details={"coding_agent": "Codex"},
        )

    def _check_required_assets(
        self,
        *,
        name: str,
        details_key: str,
        error_code: str,
        message: str,
        failure_message: str,
        root: Path,
        required_paths: Sequence[str],
    ) -> DiagnosticCheck:
        missing = [path for path in required_paths if not (root / path).exists()]
        if missing:
            return DiagnosticCheck(
                name=name,
                status=CheckStatus.FAIL,
                error_code=error_code,
                message=failure_message,
                details={
                    details_key: str(root),
                    "missing_assets": ", ".join(missing),
                },
            )
        return DiagnosticCheck(
            name=name,
            status=CheckStatus.PASS,
            message=message,
            details={details_key: str(root)},
        )

    def _check_tool(
        self,
        command: str,
        *,
        name: str,
        message: str,
        error_code: str,
        failure_message: str,
        remediation: str,
    ) -> DiagnosticCheck:
        path = self.tools.find(command)
        if path is None:
            return DiagnosticCheck(
                name=name,
                status=CheckStatus.FAIL,
                error_code=error_code,
                message=failure_message,
                details={"remediation": remediation},
            )
        return DiagnosticCheck(
            name=name,
            status=CheckStatus.PASS,
            message=message,
            details={"path": path},
        )

    def _copy_tree(
        self, *, source: Path, destination: Path, prefix: str | None = None
    ) -> list[str]:
        created_paths: list[str] = []
        for source_path in sorted(source.rglob("*")):
            relative_path = source_path.relative_to(source)
            destination_path = destination / relative_path
            if source_path.is_dir():
                destination_path.mkdir(parents=True, exist_ok=True)
                continue
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            if (
                prefix is None
                and relative_path.parts[:2] == (".auto-bean", "memory")
                and destination_path.exists()
            ):
                continue
            shutil.copy2(source_path, destination_path)
            if destination_path.suffix == ".sh" or "scripts" in relative_path.parts:
                ensure_executable(destination_path)
            path_text = relative_path.as_posix()
            created_paths.append(
                f"{prefix}/{path_text}" if prefix is not None else path_text
            )
        return created_paths

    def _planned_workspace_updates(
        self,
        *,
        target_directory: Path,
        template_directory: Path,
        skill_sources_directory: Path,
    ) -> list[dict[str, object]]:
        changes: list[dict[str, object]] = []
        managed_files = [(template_directory / "AGENTS.md", Path("AGENTS.md"))]
        managed_files.extend(
            (
                source_path,
                Path(".agents")
                / "skills"
                / source_path.relative_to(skill_sources_directory),
            )
            for source_path in sorted(skill_sources_directory.rglob("*"))
            if source_path.is_file()
        )
        for source_path, relative_target in managed_files:
            target_path = target_directory / relative_target
            if (
                target_path.exists()
                and source_path.read_bytes() == target_path.read_bytes()
            ):
                continue
            changes.append(
                {
                    "path": relative_target.as_posix(),
                    "source_path": str(source_path),
                    "diff": self._file_diff(
                        source_path=source_path,
                        target_path=target_path,
                        relative_path=relative_target.as_posix(),
                    ),
                }
            )
        return changes

    def _file_diff(
        self, *, source_path: Path, target_path: Path, relative_path: str
    ) -> str:
        source_text = source_path.read_text(encoding="utf-8").splitlines(keepends=True)
        if target_path.exists():
            target_text = target_path.read_text(encoding="utf-8").splitlines(
                keepends=True
            )
        else:
            target_text = []
        return "".join(
            unified_diff(
                target_text,
                source_text,
                fromfile=f"{relative_path} (workspace)",
                tofile=f"{relative_path} (packaged)",
            )
        )

    def _write_workspace_scripts(self, target_directory: Path) -> list[str]:
        scripts_directory = target_directory / "scripts"
        scripts_directory.mkdir(exist_ok=True)
        created_paths: list[str] = []
        for relative_path, content, executable in (
            (".gitignore", ".venv/\n__pycache__/\n*.pyc\n.DS_Store\n", False),
            (
                "scripts/validate-ledger.sh",
                "#!/bin/sh\nset -eu\n./.venv/bin/bean-check ledger.beancount\n",
                True,
            ),
            (
                "scripts/open-fava.sh",
                "#!/bin/sh\nset -eu\n./.venv/bin/fava ledger.beancount\n",
                True,
            ),
        ):
            path = target_directory / relative_path
            path.write_text(content, encoding="utf-8")
            if executable:
                ensure_executable(path)
            created_paths.append(relative_path)
        return created_paths

    def _bootstrap_workspace_runtime(self, target_directory: Path) -> DiagnosticCheck:
        uv_path = self.tools.find("uv")
        if uv_path is None:
            return DiagnosticCheck(
                name="workspace_runtime_bootstrapped",
                status=CheckStatus.FAIL,
                error_code="missing_uv",
                message="The 'uv' command is required to bootstrap the workspace runtime.",
                details={
                    "remediation": (
                        "Install uv, then rerun 'auto-bean init <PROJECT-NAME>' so the workspace "
                        "can install Beancount, Fava, and Docling locally."
                    ),
                },
            )
        venv_command = [uv_path, "venv", ".venv"]
        venv_result = self.commands.run(venv_command, cwd=target_directory)
        if venv_result.returncode != 0:
            return DiagnosticCheck(
                name="workspace_runtime_bootstrapped",
                status=CheckStatus.FAIL,
                error_code="workspace_runtime_bootstrap_failed",
                message="Failed to create the workspace virtual environment.",
                details={
                    "bootstrap_command": " ".join(venv_command),
                    "stdout": venv_result.stdout,
                    "stderr": venv_result.stderr,
                },
            )
        install_command = [
            uv_path,
            "pip",
            "install",
            "--python",
            str(target_directory / ".venv" / "bin" / "python"),
            "beancount",
            "fava",
            "docling",
        ]
        install_result = self.commands.run(install_command, cwd=target_directory)
        if install_result.returncode != 0:
            return DiagnosticCheck(
                name="workspace_runtime_bootstrapped",
                status=CheckStatus.FAIL,
                error_code="workspace_runtime_bootstrap_failed",
                message="Failed to install Beancount, Fava, and Docling into the workspace runtime.",
                details={
                    "bootstrap_command": " ".join(install_command),
                    "stdout": install_result.stdout,
                    "stderr": install_result.stderr,
                    "remediation": (
                        "Docling must be available in the workspace-local runtime before statement "
                        "intake is ready. Resolve the installation failure, then rerun "
                        "'auto-bean init <PROJECT-NAME>'."
                    ),
                },
            )
        return DiagnosticCheck(
            name="workspace_runtime_bootstrapped",
            status=CheckStatus.PASS,
            message="Workspace runtime bootstrapped with Beancount, Fava, and Docling.",
            details={
                "bootstrap_commands": [
                    " ".join(venv_command),
                    " ".join(install_command),
                ]
            },
        )

    def _bean_check_command(self, target_directory: Path) -> list[str]:
        return [
            str(target_directory / ".venv" / "bin" / "bean-check"),
            str(target_directory / "ledger.beancount"),
        ]

    def _run_workspace_command_check(
        self,
        *,
        command: Sequence[str],
        cwd: Path,
        name: str,
        success_message: str,
        error_code: str,
        failure_message: str,
        detail_key: str,
        success_details: dict[str, object] | None = None,
        failure_details: dict[str, object] | None = None,
    ) -> DiagnosticCheck:
        result = self.commands.run(command, cwd=cwd)
        command_text = " ".join(command)
        if result.returncode != 0:
            return DiagnosticCheck(
                name=name,
                status=CheckStatus.FAIL,
                error_code=error_code,
                message=failure_message,
                details={
                    detail_key: command_text,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    **(failure_details or {}),
                },
            )
        return DiagnosticCheck(
            name=name,
            status=CheckStatus.PASS,
            message=success_message,
            details={detail_key: command_text, **(success_details or {})},
        )

    def _validate_generated_ledger(self, target_directory: Path) -> DiagnosticCheck:
        command = self._bean_check_command(target_directory)
        return self._run_workspace_command_check(
            command=command,
            cwd=target_directory,
            name="ledger_validation",
            success_message="Generated ledger validated successfully.",
            error_code="invalid_generated_ledger",
            failure_message="Generated ledger failed validation.",
            detail_key="validation_command",
            success_details={
                "python_executable": str(target_directory / ".venv" / "bin" / "python")
            },
        )

    def _check_workspace_fava_available(
        self, target_directory: Path
    ) -> DiagnosticCheck:
        command = [str(target_directory / ".venv" / "bin" / "fava"), "--version"]
        return self._run_workspace_command_check(
            command=command,
            cwd=target_directory,
            name="workspace_fava_available",
            success_message="Fava is runnable from the workspace runtime.",
            error_code="workspace_fava_unavailable",
            failure_message="Fava is not runnable from the workspace runtime.",
            detail_key="fava_command",
        )

    def _check_workspace_docling_available(
        self, target_directory: Path
    ) -> DiagnosticCheck:
        command = [str(target_directory / ".venv" / "bin" / "docling"), "--version"]
        return self._run_workspace_command_check(
            command=command,
            cwd=target_directory,
            name="workspace_docling_available",
            success_message="Docling is runnable from the workspace runtime.",
            error_code="workspace_docling_unavailable",
            failure_message="Docling is not runnable from the workspace runtime.",
            detail_key="docling_command",
            failure_details={
                "remediation": (
                    "Statement intake is not ready until the workspace-local Docling CLI is "
                    "available. Fix the Docling installation, then rerun 'auto-bean init "
                    "<PROJECT-NAME>'."
                )
            },
        )

    def _create_initial_git_commit(
        self, target_directory: Path, git_path: str
    ) -> DiagnosticCheck:
        add_command = [git_path, "add", "-A"]
        add_result = self.commands.run(add_command, cwd=target_directory)
        if add_result.returncode != 0:
            return DiagnosticCheck(
                name="workspace_git_initial_commit",
                status=CheckStatus.FAIL,
                error_code="workspace_git_commit_failed",
                message="Failed to stage the initial workspace files.",
                details={
                    "git_command": " ".join(add_command),
                    "stdout": add_result.stdout,
                    "stderr": add_result.stderr,
                },
            )
        commit_command = [git_path, "commit", "-m", "Initial workspace scaffold"]
        commit_result = self.commands.run(commit_command, cwd=target_directory)
        if commit_result.returncode != 0:
            return DiagnosticCheck(
                name="workspace_git_initial_commit",
                status=CheckStatus.FAIL,
                error_code="workspace_git_commit_failed",
                message="Failed to create the initial workspace commit.",
                details={
                    "git_command": " ".join(commit_command),
                    "stdout": commit_result.stdout,
                    "stderr": commit_result.stderr,
                },
            )
        return DiagnosticCheck(
            name="workspace_git_initial_commit",
            status=CheckStatus.PASS,
            message="Workspace files staged and committed.",
            details={
                "git_commands": [" ".join(add_command), " ".join(commit_command)],
                "initial_commit_message": "Initial workspace scaffold",
            },
        )

    def _run_command_check(
        self,
        display_command: Sequence[str],
        *,
        resolved_command: Sequence[str],
        cwd: Path,
        name: str,
        success_message: str,
        error_code: str,
        failure_message: str,
        detail_key: str,
    ) -> DiagnosticCheck:
        result = self.commands.run(resolved_command, cwd=cwd)
        if result.returncode != 0:
            return DiagnosticCheck(
                name=name,
                status=CheckStatus.FAIL,
                error_code=error_code,
                message=failure_message,
                details={
                    detail_key: " ".join(display_command),
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
            )
        return DiagnosticCheck(
            name=name,
            status=CheckStatus.PASS,
            message=success_message,
            details={detail_key: " ".join(display_command)},
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
            ".auto-bean",
            ".agents",
            "beancount",
            "docs",
            "scripts",
            "statements",
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


def ensure_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | S_IEXEC)


def sanitize_project_name(project_name: str) -> bool:
    return bool(
        re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?", project_name)
    )


def looks_like_path(target: str) -> bool:
    path = Path(target).expanduser()
    return (
        path.is_absolute()
        or len(path.parts) > 1
        or target.startswith((".", "~"))
        or target.endswith(("/", "\\"))
    )


def build_init_service(start: Path | None = None) -> InitService:
    return InitService(
        paths=ProjectPaths(start=start),
        platform=PlatformProbe(),
        tools=ToolProbe(),
        commands=CommandRunner(),
    )
