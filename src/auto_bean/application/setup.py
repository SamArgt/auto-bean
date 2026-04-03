from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import shutil

from auto_bean.domain.setup import (
    CheckStatus,
    CommandOutcome,
    DiagnosticCheck,
    ErrorCategory,
)
from auto_bean.infrastructure.setup import (
    CommandExecutor,
    CommandRunner,
    looks_like_path,
    PlatformInspector,
    PlatformProbe,
    PromptResponder,
    ProjectPaths,
    ToolLocator,
    ToolProbe,
    copy_skill_sources,
    copy_workspace_template,
    current_time,
    ensure_executable,
    sanitize_project_name,
)

type ProgressReporter = Callable[[DiagnosticCheck], None]


@dataclass
class SetupService:
    paths: ProjectPaths
    platform_probe: PlatformInspector
    tool_probe: ToolLocator
    command_runner: CommandExecutor
    prompt: PromptResponder = input
    progress_reporter: ProgressReporter | None = None

    def init(
        self, project_name: str, *, coding_agent: str | None = None
    ) -> CommandOutcome:
        started = current_time()
        working_directory = self.paths.working_directory
        target_directory, target_input_type = self._target_workspace_path(project_name)
        target_preexisted = target_directory.exists()
        template_directory = self.paths.workspace_template_directory
        skill_sources_directory = self.paths.skill_sources_directory
        init_context = {
            "project_name": project_name,
            "target_input_type": target_input_type,
            "working_directory": str(working_directory),
            "target_directory": str(target_directory),
            "template_directory": str(template_directory),
            "skill_sources_directory": str(skill_sources_directory),
        }

        checks: list[DiagnosticCheck] = []

        environment_check = self._check_supported_environment()
        self._record_check(checks, environment_check)
        if environment_check.status is CheckStatus.FAIL:
            return self._result(
                workflow="init",
                status="failed",
                error_code=environment_check.error_code,
                error_category=self._classify_error(environment_check.error_code),
                message=environment_check.message,
                details=init_context | environment_check.details,
                checks=tuple(checks),
                started=started,
            )

        project_name_check = self._validate_project_name(project_name, target_directory)
        self._record_check(checks, project_name_check)
        if project_name_check.status is CheckStatus.FAIL:
            return self._result(
                workflow="init",
                status="failed",
                error_code=project_name_check.error_code,
                error_category=self._classify_error(project_name_check.error_code),
                message=project_name_check.message,
                details=init_context | project_name_check.details,
                checks=tuple(checks),
                started=started,
            )

        coding_agent = coding_agent or self.prompt_for_coding_agent()
        coding_agent_check = self._validate_coding_agent(coding_agent)
        self._record_check(checks, coding_agent_check)
        if coding_agent_check.status is CheckStatus.FAIL:
            return self._result(
                workflow="init",
                status="failed",
                error_code=coding_agent_check.error_code,
                error_category=self._classify_error(coding_agent_check.error_code),
                message=coding_agent_check.message,
                details=init_context | coding_agent_check.details,
                checks=tuple(checks),
                started=started,
            )
        template_check = self._validate_template_directory(template_directory)
        self._record_check(checks, template_check)
        if template_check.status is CheckStatus.FAIL:
            return self._result(
                workflow="init",
                status="failed",
                error_code=template_check.error_code,
                error_category=self._classify_error(template_check.error_code),
                message=template_check.message,
                details=init_context | template_check.details,
                checks=tuple(checks),
                started=started,
            )
        skill_sources_check = self._validate_skill_sources_directory(
            skill_sources_directory
        )
        self._record_check(checks, skill_sources_check)
        if skill_sources_check.status is CheckStatus.FAIL:
            return self._result(
                workflow="init",
                status="failed",
                error_code=skill_sources_check.error_code,
                error_category=self._classify_error(skill_sources_check.error_code),
                message=skill_sources_check.message,
                details=init_context | skill_sources_check.details,
                checks=tuple(checks),
                started=started,
            )

        target_directory.mkdir(parents=True, exist_ok=True)
        created_paths = copy_workspace_template(template_directory, target_directory)
        installed_skill_paths = self._materialize_workspace_skills(
            target_directory, skill_sources_directory
        )
        created_paths.extend(installed_skill_paths)
        runtime_environment_check = self._check_uv_available()
        self._record_check(checks, runtime_environment_check)
        if runtime_environment_check.status is CheckStatus.FAIL:
            self._cleanup_failed_workspace(
                target_directory, preserve_root=target_preexisted
            )
            return self._result(
                workflow="init",
                status="failed",
                error_code=runtime_environment_check.error_code,
                error_category=self._classify_error(
                    runtime_environment_check.error_code
                ),
                message=runtime_environment_check.message,
                details=init_context
                | {
                    "coding_agent": coding_agent,
                    "created_paths": created_paths,
                    **runtime_environment_check.details,
                },
                checks=tuple(checks),
                started=started,
            )
        scaffold_check = DiagnosticCheck(
            name="workspace_scaffolded",
            status=CheckStatus.PASS,
            message="Workspace template copied successfully.",
            details={
                "target_directory": str(target_directory),
                "created_file_count": len(created_paths),
            },
        )
        self._record_check(checks, scaffold_check)

        git_check = self._initialize_workspace_git_repo(target_directory)
        self._record_check(checks, git_check)
        if git_check.status is CheckStatus.FAIL:
            self._cleanup_failed_workspace(
                target_directory, preserve_root=target_preexisted
            )
            blocked_details = init_context | {
                "coding_agent": coding_agent,
                "created_paths": created_paths,
                "key_files": [
                    "ledger.beancount",
                    "AGENTS.md",
                    ".agents/skills/auto-bean-apply/SKILL.md",
                    ".agents/skills/shared/mutation-pipeline.md",
                ],
                "validation_status": "blocked",
                **git_check.details,
            }
            return self._result(
                workflow="init",
                status="failed",
                error_code=git_check.error_code,
                error_category=self._classify_error(git_check.error_code),
                message=git_check.message,
                details=blocked_details,
                checks=tuple(checks),
                started=started,
            )

        workspace_runtime_check = self._bootstrap_workspace_runtime(target_directory)
        self._record_check(checks, workspace_runtime_check)
        if workspace_runtime_check.status is CheckStatus.FAIL:
            self._cleanup_failed_workspace(
                target_directory, preserve_root=target_preexisted
            )
            blocked_details = init_context | {
                "coding_agent": coding_agent,
                "created_paths": created_paths,
                "key_files": [
                    "ledger.beancount",
                    "AGENTS.md",
                    ".agents/skills/auto-bean-apply/SKILL.md",
                    ".agents/skills/shared/mutation-pipeline.md",
                ],
                "validation_status": "blocked",
                **workspace_runtime_check.details,
            }
            return self._result(
                workflow="init",
                status="failed",
                error_code=workspace_runtime_check.error_code,
                error_category=self._classify_error(workspace_runtime_check.error_code),
                message=workspace_runtime_check.message,
                details=blocked_details,
                checks=tuple(checks),
                started=started,
            )
        self._materialize_workspace_scripts(target_directory)
        created_paths.extend(
            [
                ".gitignore",
                "scripts/validate-ledger.sh",
                "scripts/open-fava.sh",
            ]
        )
        validation_command = self._resolve_bean_check_command(target_directory)
        validation_check = self._validate_generated_ledger(
            validation_command, target_directory
        )
        self._record_check(checks, validation_check)
        fava_check = self._check_workspace_fava_available(target_directory)
        self._record_check(checks, fava_check)
        details: dict[str, object] = init_context | {
            "coding_agent": coding_agent,
            "created_paths": created_paths,
            "key_files": [
                "ledger.beancount",
                "AGENTS.md",
                ".agents/skills/auto-bean-apply/SKILL.md",
                ".agents/skills/shared/mutation-pipeline.md",
            ],
            "validation_command": " ".join(validation_command),
            "workspace_python": str(target_directory / ".venv" / "bin" / "python"),
            "workspace_bean_check": str(
                target_directory / ".venv" / "bin" / "bean-check"
            ),
            "workspace_fava": str(target_directory / ".venv" / "bin" / "fava"),
            "validation_status": "passed"
            if validation_check.status is CheckStatus.PASS
            else "failed",
            "fava_status": "passed"
            if fava_check.status is CheckStatus.PASS
            else "failed",
            "next_steps": [
                f"cd {target_directory}",
                "Review AGENTS.md for the Codex-first workspace workflow and path guide.",
                "./scripts/validate-ledger.sh",
                "./scripts/open-fava.sh",
            ],
        }
        failed_check = next(
            (
                check
                for check in (validation_check, fava_check)
                if check.status is CheckStatus.FAIL
            ),
            None,
        )
        if failed_check is not None:
            self._cleanup_failed_workspace(
                target_directory, preserve_root=target_preexisted
            )
        status = "ok" if failed_check is None else "failed"
        error_code = None if failed_check is None else failed_check.error_code
        message = (
            f"Workspace created at {target_directory} and validated successfully."
            if failed_check is None
            else failed_check.message
        )
        if failed_check is None:
            commit_check = self._create_initial_workspace_commit(target_directory)
            self._record_check(checks, commit_check)
            if commit_check.status is CheckStatus.FAIL:
                self._cleanup_failed_workspace(
                    target_directory, preserve_root=target_preexisted
                )
                status = "failed"
                error_code = commit_check.error_code
                message = commit_check.message
        return self._result(
            workflow="init",
            status=status,
            error_code=error_code,
            error_category=self._classify_error(error_code),
            message=message,
            details=details | validation_check.details,
            checks=tuple(checks),
            started=started,
        )

    def _record_check(
        self, checks: list[DiagnosticCheck], check: DiagnosticCheck
    ) -> None:
        checks.append(check)
        if self.progress_reporter is not None:
            self.progress_reporter(check)

    def execution_error(
        self,
        workflow: str,
        *,
        details: dict[str, object],
        message: str = "Workflow execution failed unexpectedly.",
    ) -> CommandOutcome:
        started = current_time()
        return self._result(
            workflow=workflow,
            status="failed",
            error_code="execution_error",
            error_category=ErrorCategory.EXECUTION_ERROR,
            message=message,
            details=details,
            checks=(),
            started=started,
        )

    def _check_supported_environment(self) -> DiagnosticCheck:
        environment = self.platform_probe.inspect()
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
            error_code=None,
            message="Supported macOS environment detected.",
            details={
                "detected_system": environment.system,
                "detected_release": environment.release,
                "detected_machine": environment.machine,
                "python_version": environment.python_version,
            },
        )

    def _check_uv_available(self) -> DiagnosticCheck:
        uv_path = self.tool_probe.find("uv")
        if uv_path is None:
            return DiagnosticCheck(
                name="uv_available",
                status=CheckStatus.FAIL,
                error_code="missing_uv",
                message="The 'uv' command is required but was not found.",
                details={
                    "remediation": (
                        "Install uv, then run 'uv tool install --from . --force auto-bean'. Example: "
                        "https://docs.astral.sh/uv/getting-started/installation/"
                    ),
                },
            )
        return DiagnosticCheck(
            name="uv_available",
            status=CheckStatus.PASS,
            error_code=None,
            message="uv is available.",
            details={"path": uv_path},
        )

    def _target_workspace_path(self, project_name: str) -> tuple[Path, str]:
        working_directory = self.paths.working_directory
        if looks_like_path(project_name):
            return (
                working_directory / Path(project_name).expanduser()
            ).resolve(), "path"

        try:
            repo_root = self.paths.repo_root
        except RuntimeError:
            return (working_directory / project_name).resolve(), "name"

        if working_directory == repo_root or repo_root in working_directory.parents:
            return (repo_root.parent / project_name).resolve(), "name"
        return (working_directory / project_name).resolve(), "name"

    def _validate_project_name(
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

    def prompt_for_coding_agent(self) -> str:
        response = self.prompt(
            "Which coding agent should this workspace target? [Codex]: "
        ).strip()
        return response or "Codex"

    def _validate_coding_agent(self, coding_agent: str) -> DiagnosticCheck:
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

    def _validate_template_directory(self, template_directory: Path) -> DiagnosticCheck:
        required_paths = (
            "ledger.beancount",
            "AGENTS.md",
            "beancount/opening-balances.beancount",
        )
        missing = [
            required_path
            for required_path in required_paths
            if not (template_directory / required_path).exists()
        ]
        if missing:
            return DiagnosticCheck(
                name="workspace_template_available",
                status=CheckStatus.FAIL,
                error_code="missing_template_assets",
                message="Workspace template assets are missing.",
                details={
                    "template_directory": str(template_directory),
                    "missing_assets": ", ".join(missing),
                },
            )
        return DiagnosticCheck(
            name="workspace_template_available",
            status=CheckStatus.PASS,
            message="Workspace template assets are available.",
            details={"template_directory": str(template_directory)},
        )

    def _validate_skill_sources_directory(
        self, skill_sources_directory: Path
    ) -> DiagnosticCheck:
        required_paths = (
            "auto-bean-apply/SKILL.md",
            "auto-bean-apply/agents/openai.yaml",
            "shared/mutation-pipeline.md",
            "shared/mutation-authority-matrix.md",
        )
        missing = [
            required_path
            for required_path in required_paths
            if not (skill_sources_directory / required_path).exists()
        ]
        if missing:
            return DiagnosticCheck(
                name="skill_sources_available",
                status=CheckStatus.FAIL,
                error_code="missing_skill_sources",
                message="Authored skill source assets are missing.",
                details={
                    "skill_sources_directory": str(skill_sources_directory),
                    "missing_assets": ", ".join(missing),
                },
            )
        return DiagnosticCheck(
            name="skill_sources_available",
            status=CheckStatus.PASS,
            message="Authored skill source assets are available.",
            details={"skill_sources_directory": str(skill_sources_directory)},
        )

    def _materialize_workspace_skills(
        self,
        target_directory: Path,
        skill_sources_directory: Path,
    ) -> list[str]:
        skills_directory = target_directory / ".agents" / "skills"
        skills_directory.mkdir(parents=True, exist_ok=True)
        return [
            f".agents/skills/{path}"
            for path in copy_skill_sources(skill_sources_directory, skills_directory)
        ]

    def _materialize_workspace_scripts(self, target_directory: Path) -> None:
        scripts_directory = target_directory / "scripts"
        scripts_directory.mkdir(exist_ok=True)
        gitignore_path = target_directory / ".gitignore"
        gitignore_path.write_text(
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

    def _resolve_bean_check_command(self, target_directory: Path) -> list[str]:
        ledger_path = target_directory / "ledger.beancount"
        return [
            str(target_directory / ".venv" / "bin" / "bean-check"),
            str(ledger_path),
        ]

    def _initialize_workspace_git_repo(self, target_directory: Path) -> DiagnosticCheck:
        git_path = self.tool_probe.find("git")
        if git_path is None:
            return DiagnosticCheck(
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

        init_command = [git_path, "init"]
        init_result = self.command_runner.run(init_command, cwd=target_directory)
        if init_result.returncode != 0:
            return DiagnosticCheck(
                name="workspace_git_initialized",
                status=CheckStatus.FAIL,
                error_code="workspace_git_init_failed",
                message="Failed to initialize the workspace as a Git repository.",
                details={
                    "git_command": " ".join(init_command),
                    "stdout": init_result.stdout,
                    "stderr": init_result.stderr,
                },
            )

        return DiagnosticCheck(
            name="workspace_git_initialized",
            status=CheckStatus.PASS,
            message="Workspace Git repository initialized.",
            details={"git_command": " ".join(init_command)},
        )

    def _create_initial_workspace_commit(
        self, target_directory: Path
    ) -> DiagnosticCheck:
        git_path = self.tool_probe.find("git")
        if git_path is None:
            return DiagnosticCheck(
                name="workspace_git_initial_commit",
                status=CheckStatus.FAIL,
                error_code="missing_git",
                message="The 'git' command is required to create the initial workspace commit.",
                details={
                    "remediation": (
                        "Install Git, then rerun 'auto-bean init <PROJECT-NAME>' so the workspace "
                        "starts with an initial commit."
                    ),
                },
            )

        add_command = [git_path, "add", "-A"]
        add_result = self.command_runner.run(add_command, cwd=target_directory)
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
        commit_result = self.command_runner.run(commit_command, cwd=target_directory)
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
                "git_commands": [
                    " ".join(add_command),
                    " ".join(commit_command),
                ],
                "initial_commit_message": "Initial workspace scaffold",
            },
        )

    def _bootstrap_workspace_runtime(self, target_directory: Path) -> DiagnosticCheck:
        uv_path = self.tool_probe.find("uv")
        if uv_path is None:
            return DiagnosticCheck(
                name="workspace_runtime_bootstrapped",
                status=CheckStatus.FAIL,
                error_code="missing_uv",
                message="The 'uv' command is required to bootstrap the workspace runtime.",
                details={
                    "remediation": (
                        "Install uv, then rerun 'auto-bean init <PROJECT-NAME>' so the workspace "
                        "can install Beancount and Fava locally."
                    ),
                },
            )
        venv_command = [uv_path, "venv", ".venv"]
        venv_result = self.command_runner.run(venv_command, cwd=target_directory)
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
        ]
        install_result = self.command_runner.run(install_command, cwd=target_directory)
        if install_result.returncode != 0:
            return DiagnosticCheck(
                name="workspace_runtime_bootstrapped",
                status=CheckStatus.FAIL,
                error_code="workspace_runtime_bootstrap_failed",
                message="Failed to install Beancount and Fava into the workspace runtime.",
                details={
                    "bootstrap_command": " ".join(install_command),
                    "stdout": install_result.stdout,
                    "stderr": install_result.stderr,
                },
            )
        return DiagnosticCheck(
            name="workspace_runtime_bootstrapped",
            status=CheckStatus.PASS,
            message="Workspace runtime bootstrapped with Beancount and Fava.",
            details={
                "bootstrap_commands": [
                    " ".join(venv_command),
                    " ".join(install_command),
                ],
            },
        )

    def _validate_generated_ledger(
        self,
        validation_command: list[str],
        target_directory: Path,
    ) -> DiagnosticCheck:
        result = self.command_runner.run(validation_command, cwd=target_directory)
        if result.returncode != 0:
            return DiagnosticCheck(
                name="ledger_validation",
                status=CheckStatus.FAIL,
                error_code="invalid_generated_ledger",
                message="Generated ledger failed validation.",
                details={
                    "validation_command": " ".join(validation_command),
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
            )
        return DiagnosticCheck(
            name="ledger_validation",
            status=CheckStatus.PASS,
            message="Generated ledger validated successfully.",
            details={
                "validation_command": " ".join(validation_command),
                "python_executable": str(target_directory / ".venv" / "bin" / "python"),
            },
        )

    def _check_workspace_fava_available(
        self, target_directory: Path
    ) -> DiagnosticCheck:
        fava_command = [str(target_directory / ".venv" / "bin" / "fava"), "--version"]
        result = self.command_runner.run(fava_command, cwd=target_directory)
        if result.returncode != 0:
            return DiagnosticCheck(
                name="workspace_fava_available",
                status=CheckStatus.FAIL,
                error_code="workspace_fava_unavailable",
                message="Fava is not runnable from the workspace runtime.",
                details={
                    "fava_command": " ".join(fava_command),
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
            )
        return DiagnosticCheck(
            name="workspace_fava_available",
            status=CheckStatus.PASS,
            message="Fava is runnable from the workspace runtime.",
            details={"fava_command": " ".join(fava_command)},
        )

    def _cleanup_failed_workspace(
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

        if (
            not preserve_root
            and target_directory.exists()
            and not any(target_directory.iterdir())
        ):
            target_directory.rmdir()

    def _result(
        self,
        *,
        workflow: str,
        status: str,
        error_code: str | None,
        error_category: ErrorCategory | None,
        message: str,
        details: dict[str, object],
        checks: tuple[DiagnosticCheck, ...],
        started: float,
    ) -> CommandOutcome:
        return CommandOutcome(
            workflow=workflow,
            status=status,
            error_code=error_code,
            error_category=error_category,
            message=message,
            details=details,
            checks=checks,
            duration_seconds=current_time() - started,
        )

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
        }:
            return ErrorCategory.VALIDATION_FAILURE
        return ErrorCategory.EXECUTION_ERROR


def build_setup_service(start: Path | None = None) -> SetupService:
    return SetupService(
        paths=ProjectPaths(start=start),
        platform_probe=PlatformProbe(),
        tool_probe=ToolProbe(),
        command_runner=CommandRunner(),
    )
