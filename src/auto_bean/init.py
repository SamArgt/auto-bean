from __future__ import annotations

import platform
import re
import shutil
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
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

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "status": self.status.value,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
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


@dataclass
class InitService:
    paths: ProjectPaths
    platform: PlatformInspector
    tools: ToolLocator
    commands: CommandExecutor
    prompt: PromptResponder = input
    progress_reporter: ProgressReporter | None = None

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

        for check in (
            self._check_environment(),
            self._check_target(project_name, target_directory),
        ):
            self._record(checks, check)
            if check.status is CheckStatus.FAIL:
                return self._failure(
                    checks=checks,
                    context=context,
                    started=started,
                    check=check,
                )

        selected_agent = coding_agent or self.prompt_for_coding_agent()
        for check in (
            self._check_coding_agent(selected_agent),
            self._check_required_assets(
                name="workspace_template_available",
                error_code="missing_template_assets",
                message="Workspace template assets are available.",
                failure_message="Workspace template assets are missing.",
                root=Path(context.template_directory),
                required_paths=(
                    "ledger.beancount",
                    "AGENTS.md",
                    "beancount/accounts.beancount",
                    "beancount/opening-balances.beancount",
                    "statements/parsed/.gitkeep",
                    "statements/import-status.yml",
                ),
            ),
            self._check_required_assets(
                name="skill_sources_available",
                error_code="missing_skill_sources",
                message="Authored skill source assets are available.",
                failure_message="Authored skill source assets are missing.",
                root=Path(context.skill_sources_directory),
                required_paths=(
                    "auto-bean-apply/SKILL.md",
                    "auto-bean-apply/agents/openai.yaml",
                    "auto-bean-import/SKILL.md",
                    "auto-bean-import/agents/openai.yaml",
                    "auto-bean-import/references/account-proposal.example.json",
                    "auto-bean-import/references/parsed-statement-output.example.json",
                    "auto-bean-import/references/import-status.example.yml",
                    "shared/mutation-pipeline.md",
                    "shared/mutation-authority-matrix.md",
                ),
            ),
            self._check_tool(
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
        ):
            self._record(checks, check)
            if check.status is CheckStatus.FAIL:
                return self._failure(
                    checks=checks,
                    context=context,
                    started=started,
                    check=check,
                )
        selected_agent = "Codex"

        target_preexisted = target_directory.exists()
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
        self._write_workspace_scripts(target_directory)
        created_paths.extend(
            [".gitignore", "scripts/validate-ledger.sh", "scripts/open-fava.sh"]
        )
        blocked_details: dict[str, object] = {
            "coding_agent": selected_agent,
            "created_paths": created_paths,
            "key_files": [
                "ledger.beancount",
                "AGENTS.md",
                ".agents/skills/auto-bean-apply/SKILL.md",
                ".agents/skills/auto-bean-import/SKILL.md",
                ".agents/skills/shared/mutation-pipeline.md",
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
            ),
        )

        git_path = self.tools.find("git")
        if git_path is None:
            check = DiagnosticCheck(
                name="workspace_git_initialized",
                status=CheckStatus.FAIL,
                error_code="missing_git",
                message="The 'git' command is required to initialize the workspace repository.",
                details={
                    "remediation": (
                        "Install Git, then rerun 'auto-bean init <PROJECT-NAME>' so the workspace "
                        "starts as a repository."
                    ),
                },
            )
            self._record(checks, check)
            self._cleanup_workspace(target_directory, preserve_root=target_preexisted)
            return self._failure(
                checks=checks,
                context=context,
                started=started,
                check=check,
                extra_details={
                    **blocked_details,
                },
            )

        for check in (
            self._run_command_check(
                ["git", "init"],
                resolved_command=[git_path, "init"],
                cwd=target_directory,
                name="workspace_git_initialized",
                success_message="Workspace Git repository initialized.",
                error_code="workspace_git_init_failed",
                failure_message="Failed to initialize the workspace as a Git repository.",
                detail_key="git_command",
            ),
        ):
            self._record(checks, check)
            if check.status is CheckStatus.FAIL:
                self._cleanup_workspace(
                    target_directory, preserve_root=target_preexisted
                )
                return self._failure(
                    checks=checks,
                    context=context,
                    started=started,
                    check=check,
                    extra_details=blocked_details
                    | (
                        {"validation_status": "blocked"}
                        if check.name
                        in {
                            "workspace_runtime_bootstrapped",
                            "workspace_git_initialized",
                            "workspace_git_initial_commit",
                        }
                        else {}
                    ),
                )

        for check in (
            self._bootstrap_workspace_runtime(target_directory),
            self._validate_generated_ledger(target_directory),
            self._check_workspace_fava_available(target_directory),
            self._check_workspace_docling_available(target_directory),
            self._create_initial_git_commit(target_directory, git_path),
        ):
            self._record(checks, check)
            if check.status is CheckStatus.FAIL:
                self._cleanup_workspace(
                    target_directory, preserve_root=target_preexisted
                )
                return self._failure(
                    checks=checks,
                    context=context,
                    started=started,
                    check=check,
                    extra_details=blocked_details
                    | (
                        {"validation_status": "blocked"}
                        if check.name
                        in {
                            "workspace_runtime_bootstrapped",
                            "workspace_git_initial_commit",
                        }
                        else {}
                    ),
                )

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
                    "Use the installed .agents/skills/auto-bean-import/ workflow when you are ready to normalize statements.",
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

    def _failure(
        self,
        *,
        checks: list[DiagnosticCheck],
        context: InitContext,
        started: float,
        check: DiagnosticCheck,
        extra_details: dict[str, object] | None = None,
    ) -> CommandOutcome:
        details = context.as_details() | check.details
        if extra_details is not None:
            details |= extra_details
        return CommandOutcome(
            workflow="init",
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
        error_code: str,
        message: str,
        failure_message: str,
        root: Path,
        required_paths: Sequence[str],
    ) -> DiagnosticCheck:
        missing = [path for path in required_paths if not (root / path).exists()]
        details_key = (
            "template_directory" if "template" in name else "skill_sources_directory"
        )
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
            shutil.copy2(source_path, destination_path)
            if destination_path.suffix == ".sh" or "scripts" in relative_path.parts:
                ensure_executable(destination_path)
            path_text = relative_path.as_posix()
            created_paths.append(
                f"{prefix}/{path_text}" if prefix is not None else path_text
            )
        return created_paths

    def _write_workspace_scripts(self, target_directory: Path) -> None:
        scripts_directory = target_directory / "scripts"
        scripts_directory.mkdir(exist_ok=True)
        (target_directory / ".gitignore").write_text(
            ".venv/\n__pycache__/\n*.pyc\n.DS_Store\n",
            encoding="utf-8",
        )
        validate_script = scripts_directory / "validate-ledger.sh"
        validate_script.write_text(
            "#!/bin/sh\nset -eu\n./.venv/bin/bean-check ledger.beancount\n",
            encoding="utf-8",
        )
        ensure_executable(validate_script)
        fava_script = scripts_directory / "open-fava.sh"
        fava_script.write_text(
            "#!/bin/sh\nset -eu\n./.venv/bin/fava ledger.beancount\n",
            encoding="utf-8",
        )
        ensure_executable(fava_script)

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

    def _validate_generated_ledger(self, target_directory: Path) -> DiagnosticCheck:
        command = self._bean_check_command(target_directory)
        result = self.commands.run(command, cwd=target_directory)
        if result.returncode != 0:
            return DiagnosticCheck(
                name="ledger_validation",
                status=CheckStatus.FAIL,
                error_code="invalid_generated_ledger",
                message="Generated ledger failed validation.",
                details={
                    "validation_command": " ".join(command),
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
            )
        return DiagnosticCheck(
            name="ledger_validation",
            status=CheckStatus.PASS,
            message="Generated ledger validated successfully.",
            details={
                "validation_command": " ".join(command),
                "python_executable": str(target_directory / ".venv" / "bin" / "python"),
            },
        )

    def _check_workspace_fava_available(
        self, target_directory: Path
    ) -> DiagnosticCheck:
        command = [str(target_directory / ".venv" / "bin" / "fava"), "--version"]
        result = self.commands.run(command, cwd=target_directory)
        if result.returncode != 0:
            return DiagnosticCheck(
                name="workspace_fava_available",
                status=CheckStatus.FAIL,
                error_code="workspace_fava_unavailable",
                message="Fava is not runnable from the workspace runtime.",
                details={
                    "fava_command": " ".join(command),
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
            )
        return DiagnosticCheck(
            name="workspace_fava_available",
            status=CheckStatus.PASS,
            message="Fava is runnable from the workspace runtime.",
            details={"fava_command": " ".join(command)},
        )

    def _check_workspace_docling_available(
        self, target_directory: Path
    ) -> DiagnosticCheck:
        command = [str(target_directory / ".venv" / "bin" / "docling"), "--version"]
        result = self.commands.run(command, cwd=target_directory)
        if result.returncode != 0:
            return DiagnosticCheck(
                name="workspace_docling_available",
                status=CheckStatus.FAIL,
                error_code="workspace_docling_unavailable",
                message="Docling is not runnable from the workspace runtime.",
                details={
                    "docling_command": " ".join(command),
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "remediation": (
                        "Statement intake is not ready until the workspace-local Docling CLI is "
                        "available. Fix the Docling installation, then rerun 'auto-bean init "
                        "<PROJECT-NAME>'."
                    ),
                },
            )
        return DiagnosticCheck(
            name="workspace_docling_available",
            status=CheckStatus.PASS,
            message="Docling is runnable from the workspace runtime.",
            details={"docling_command": " ".join(command)},
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
            "workspace_runtime_bootstrap_failed",
            "workspace_git_init_failed",
            "workspace_git_commit_failed",
        }:
            return ErrorCategory.PREREQUISITE_FAILURE
        if error_code in {
            "unsafe_project_name",
            "non_empty_target_directory",
            "non_directory_target_path",
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
