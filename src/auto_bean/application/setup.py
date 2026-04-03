from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
import shutil

from auto_bean.domain.setup import (
    ArtifactRecord,
    CheckStatus,
    DiagnosticCheck,
    ErrorCategory,
    WorkflowEvent,
    WorkflowResult,
)
from auto_bean.infrastructure.setup import (
    ArtifactWriter,
    CommandExecutor,
    CommandRunner,
    PlatformInspector,
    PlatformProbe,
    PromptResponder,
    ProjectPaths,
    ToolLocator,
    ToolProbe,
    copy_skill_sources,
    copy_workspace_template,
    current_time,
    current_timestamp,
    ensure_executable,
    generate_run_id,
    sanitize_project_name,
    WorkflowArtifactStore,
)


@dataclass
class SetupService:
    paths: ProjectPaths
    platform_probe: PlatformInspector
    tool_probe: ToolLocator
    command_runner: CommandExecutor
    artifact_store: ArtifactWriter = field(default_factory=WorkflowArtifactStore)
    run_id_factory: Callable[[], str] = generate_run_id
    clock: Callable[[], str] = current_timestamp
    prompt: PromptResponder = input

    def readiness(self) -> WorkflowResult:
        run_id = self.run_id_factory()
        started_at = self.clock()
        started = current_time()
        events: list[WorkflowEvent] = [
            self._event(
                run_id=run_id,
                workflow="readiness",
                stage="workflow_started",
                status=CheckStatus.PASS,
                message="Readiness workflow started.",
            )
        ]
        checks = (
            self._check_supported_environment(),
            self._check_uv_available(),
            self._check_auto_bean_on_path(),
        )
        for check in checks:
            events.append(
                self._event(
                    run_id=run_id,
                    workflow="readiness",
                    stage=check.name,
                    status=check.status,
                    message=check.message,
                    details=check.details,
                )
            )
        failed_check = next(
            (check for check in checks if check.status is CheckStatus.FAIL),
            None,
        )
        if failed_check is not None:
            return self._result(
                run_id=run_id,
                workflow="readiness",
                status="failed",
                error_code=failed_check.error_code,
                error_category=self._classify_error(failed_check.error_code),
                message=failed_check.message,
                details=failed_check.details,
                checks=checks,
                events=events,
                started_at=started_at,
                started=started,
            )

        warned_check = next(
            (check for check in checks if check.status is CheckStatus.WARN),
            None,
        )
        if warned_check is not None:
            return self._result(
                run_id=run_id,
                workflow="readiness",
                status="failed",
                error_code=warned_check.error_code,
                error_category=self._classify_error(warned_check.error_code),
                message=warned_check.message,
                details=warned_check.details,
                checks=checks,
                events=events,
                started_at=started_at,
                started=started,
            )

        return self._result(
            run_id=run_id,
            workflow="readiness",
            status="ok",
            error_code=None,
            error_category=None,
            message="Readiness check passed. auto-bean is installed and discoverable.",
            details={"command": "auto-bean --help"},
            checks=checks,
            events=events,
            started_at=started_at,
            started=started,
        )

    def init(self, project_name: str) -> WorkflowResult:
        run_id = self.run_id_factory()
        started_at = self.clock()
        started = current_time()
        events = [
            self._event(
                run_id=run_id,
                workflow="init",
                stage="workflow_started",
                status=CheckStatus.PASS,
                message="Init workflow started.",
                details={"project_name": project_name},
            )
        ]
        working_directory = self.paths.working_directory
        target_directory = self._target_workspace_path(project_name)
        target_preexisted = target_directory.exists()

        checks: list[DiagnosticCheck] = []

        project_name_check = self._validate_project_name(project_name, target_directory)
        checks.append(project_name_check)
        events.append(
            self._event(
                run_id=run_id,
                workflow="init",
                stage=project_name_check.name,
                status=project_name_check.status,
                message=project_name_check.message,
                details=project_name_check.details,
            )
        )
        if project_name_check.status is CheckStatus.FAIL:
            return self._result(
                run_id=run_id,
                workflow="init",
                status="failed",
                error_code=project_name_check.error_code,
                error_category=self._classify_error(project_name_check.error_code),
                message=project_name_check.message,
                details=project_name_check.details,
                checks=tuple(checks),
                events=events,
                started_at=started_at,
                started=started,
            )

        coding_agent = self._prompt_for_coding_agent()
        coding_agent_check = self._validate_coding_agent(coding_agent)
        checks.append(coding_agent_check)
        events.append(
            self._event(
                run_id=run_id,
                workflow="init",
                stage=coding_agent_check.name,
                status=coding_agent_check.status,
                message=coding_agent_check.message,
                details=coding_agent_check.details,
            )
        )
        if coding_agent_check.status is CheckStatus.FAIL:
            return self._result(
                run_id=run_id,
                workflow="init",
                status="failed",
                error_code=coding_agent_check.error_code,
                error_category=self._classify_error(coding_agent_check.error_code),
                message=coding_agent_check.message,
                details={
                    "project_name": project_name,
                    "working_directory": str(working_directory),
                    "target_directory": str(target_directory),
                    **coding_agent_check.details,
                },
                checks=tuple(checks),
                events=events,
                started_at=started_at,
                started=started,
            )

        template_directory = self.paths.workspace_template_directory
        template_check = self._validate_template_directory(template_directory)
        checks.append(template_check)
        events.append(
            self._event(
                run_id=run_id,
                workflow="init",
                stage=template_check.name,
                status=template_check.status,
                message=template_check.message,
                details=template_check.details,
            )
        )
        if template_check.status is CheckStatus.FAIL:
            return self._result(
                run_id=run_id,
                workflow="init",
                status="failed",
                error_code=template_check.error_code,
                error_category=self._classify_error(template_check.error_code),
                message=template_check.message,
                details={
                    "project_name": project_name,
                    "working_directory": str(working_directory),
                    "target_directory": str(target_directory),
                    **template_check.details,
                },
                checks=tuple(checks),
                events=events,
                started_at=started_at,
                started=started,
            )

        skill_sources_directory = self.paths.skill_sources_directory
        skill_sources_check = self._validate_skill_sources_directory(
            skill_sources_directory
        )
        checks.append(skill_sources_check)
        events.append(
            self._event(
                run_id=run_id,
                workflow="init",
                stage=skill_sources_check.name,
                status=skill_sources_check.status,
                message=skill_sources_check.message,
                details=skill_sources_check.details,
            )
        )
        if skill_sources_check.status is CheckStatus.FAIL:
            return self._result(
                run_id=run_id,
                workflow="init",
                status="failed",
                error_code=skill_sources_check.error_code,
                error_category=self._classify_error(skill_sources_check.error_code),
                message=skill_sources_check.message,
                details={
                    "project_name": project_name,
                    "working_directory": str(working_directory),
                    "target_directory": str(target_directory),
                    **skill_sources_check.details,
                },
                checks=tuple(checks),
                events=events,
                started_at=started_at,
                started=started,
            )

        target_directory.mkdir(parents=True, exist_ok=True)
        created_paths = copy_workspace_template(template_directory, target_directory)
        installed_skill_paths = self._materialize_workspace_skills(
            target_directory, skill_sources_directory
        )
        created_paths.extend(installed_skill_paths)
        runtime_environment_check = self._check_uv_available()
        checks.append(runtime_environment_check)
        events.append(
            self._event(
                run_id=run_id,
                workflow="init",
                stage="workspace_runtime_prerequisites",
                status=runtime_environment_check.status,
                message=runtime_environment_check.message,
                details=runtime_environment_check.details,
            )
        )
        if runtime_environment_check.status is CheckStatus.FAIL:
            self._cleanup_failed_workspace(
                target_directory, preserve_root=target_preexisted
            )
            return self._result(
                run_id=run_id,
                workflow="init",
                status="failed",
                error_code=runtime_environment_check.error_code,
                error_category=self._classify_error(
                    runtime_environment_check.error_code
                ),
                message=runtime_environment_check.message,
                details={
                    "project_name": project_name,
                    "working_directory": str(working_directory),
                    "target_directory": str(target_directory),
                    "coding_agent": coding_agent,
                    "created_paths": created_paths,
                    **runtime_environment_check.details,
                },
                checks=tuple(checks),
                events=events,
                started_at=started_at,
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
        checks.append(scaffold_check)
        events.append(
            self._event(
                run_id=run_id,
                workflow="init",
                stage=scaffold_check.name,
                status=scaffold_check.status,
                message=scaffold_check.message,
                details=scaffold_check.details,
            )
        )

        git_check = self._initialize_workspace_git_repo(target_directory)
        checks.append(git_check)
        events.append(
            self._event(
                run_id=run_id,
                workflow="init",
                stage=git_check.name,
                status=git_check.status,
                message=git_check.message,
                details=git_check.details,
            )
        )
        if git_check.status is CheckStatus.FAIL:
            self._cleanup_failed_workspace(
                target_directory, preserve_root=target_preexisted
            )
            blocked_details = {
                "project_name": project_name,
                "working_directory": str(working_directory),
                "target_directory": str(target_directory),
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
                run_id=run_id,
                workflow="init",
                status="failed",
                error_code=git_check.error_code,
                error_category=self._classify_error(git_check.error_code),
                message=git_check.message,
                details=blocked_details,
                checks=tuple(checks),
                events=events,
                started_at=started_at,
                started=started,
            )

        workspace_runtime_check = self._bootstrap_workspace_runtime(target_directory)
        checks.append(workspace_runtime_check)
        events.append(
            self._event(
                run_id=run_id,
                workflow="init",
                stage=workspace_runtime_check.name,
                status=workspace_runtime_check.status,
                message=workspace_runtime_check.message,
                details=workspace_runtime_check.details,
            )
        )
        if workspace_runtime_check.status is CheckStatus.FAIL:
            self._cleanup_failed_workspace(
                target_directory, preserve_root=target_preexisted
            )
            blocked_details = {
                "project_name": project_name,
                "working_directory": str(working_directory),
                "target_directory": str(target_directory),
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
                run_id=run_id,
                workflow="init",
                status="failed",
                error_code=workspace_runtime_check.error_code,
                error_category=self._classify_error(workspace_runtime_check.error_code),
                message=workspace_runtime_check.message,
                details=blocked_details,
                checks=tuple(checks),
                events=events,
                started_at=started_at,
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
        checks.append(validation_check)
        events.append(
            self._event(
                run_id=run_id,
                workflow="init",
                stage=validation_check.name,
                status=validation_check.status,
                message=validation_check.message,
                details=validation_check.details,
            )
        )
        fava_check = self._check_workspace_fava_available(target_directory)
        checks.append(fava_check)
        events.append(
            self._event(
                run_id=run_id,
                workflow="init",
                stage=fava_check.name,
                status=fava_check.status,
                message=fava_check.message,
                details=fava_check.details,
            )
        )
        details: dict[str, object] = {
            "project_name": project_name,
            "working_directory": str(working_directory),
            "target_directory": str(target_directory),
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
            checks.append(commit_check)
            events.append(
                self._event(
                    run_id=run_id,
                    workflow="init",
                    stage=commit_check.name,
                    status=commit_check.status,
                    message=commit_check.message,
                    details=commit_check.details,
                )
            )
            if commit_check.status is CheckStatus.FAIL:
                self._cleanup_failed_workspace(
                    target_directory, preserve_root=target_preexisted
                )
                status = "failed"
                error_code = commit_check.error_code
                message = commit_check.message
        return self._result(
            run_id=run_id,
            workflow="init",
            status=status,
            error_code=error_code,
            error_category=self._classify_error(error_code),
            message=message,
            details=details | validation_check.details,
            checks=tuple(checks),
            events=events,
            started_at=started_at,
            started=started,
        )

    def execution_error(
        self,
        workflow: str,
        *,
        details: dict[str, object],
        message: str = "Workflow execution failed unexpectedly.",
    ) -> WorkflowResult:
        run_id = self.run_id_factory()
        started_at = self.clock()
        started = current_time()
        events = [
            self._event(
                run_id=run_id,
                workflow=workflow,
                stage="workflow_started",
                status=CheckStatus.PASS,
                message=f"{workflow.capitalize()} workflow started.",
            ),
            self._event(
                run_id=run_id,
                workflow=workflow,
                stage="workflow_exception",
                status=CheckStatus.FAIL,
                message=message,
                details=details,
            ),
        ]
        return self._result(
            run_id=run_id,
            workflow=workflow,
            status="failed",
            error_code="execution_error",
            error_category=ErrorCategory.EXECUTION_ERROR,
            message=message,
            details=details,
            checks=(),
            events=events,
            started_at=started_at,
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

    def _check_auto_bean_on_path(self) -> DiagnosticCheck:
        tool_path = self.tool_probe.find("auto-bean")
        if tool_path is None:
            return DiagnosticCheck(
                name="auto_bean_on_path",
                status=CheckStatus.WARN,
                error_code="missing_auto_bean_on_path",
                message="auto-bean is not discoverable on PATH yet.",
                details={
                    "verification_command": "uv tool run --from . auto-bean readiness",
                    "remediation": (
                        "Run 'uv tool install --from . --force auto-bean' if needed. To verify the "
                        "install before PATH is fixed, run 'uv tool run --from . auto-bean readiness' "
                        "from the product repo. Then add uv's tool bin directory to PATH or run the "
                        "shell setup recommended by uv, open a new shell, and rerun 'auto-bean readiness'."
                    ),
                },
            )

        command = [tool_path, "--help"]
        result = self.command_runner.run(command)
        if result.returncode != 0:
            return DiagnosticCheck(
                name="auto_bean_on_path",
                status=CheckStatus.FAIL,
                error_code="auto_bean_unavailable",
                message="auto-bean is on PATH but is not runnable.",
                details={
                    "path": tool_path,
                    "command": " ".join(command),
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "remediation": (
                        "Run 'uv tool install --from . --force auto-bean' to reinstall the tool, "
                        "then try 'auto-bean readiness' again."
                    ),
                },
            )

        return DiagnosticCheck(
            name="auto_bean_on_path",
            status=CheckStatus.PASS,
            error_code=None,
            message="auto-bean is discoverable on PATH and runnable.",
            details={"path": tool_path, "command": " ".join(command)},
        )

    def _target_workspace_path(self, project_name: str) -> Path:
        working_directory = self.paths.working_directory
        try:
            repo_root = self.paths.repo_root
        except RuntimeError:
            return working_directory / project_name

        if working_directory == repo_root or repo_root in working_directory.parents:
            return repo_root.parent / project_name
        return working_directory / project_name

    def _validate_project_name(
        self, project_name: str, target_directory: Path
    ) -> DiagnosticCheck:
        if not sanitize_project_name(project_name):
            return DiagnosticCheck(
                name="project_name_valid",
                status=CheckStatus.FAIL,
                error_code="unsafe_project_name",
                message="Project name is unsafe. Use letters, numbers, dots, underscores, or dashes only.",
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
            message="Project name and target directory are valid.",
            details={
                "project_name": project_name,
                "target_directory": str(target_directory),
            },
        )

    def _prompt_for_coding_agent(self) -> str:
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
        run_id: str,
        workflow: str,
        status: str,
        error_code: str | None,
        error_category: ErrorCategory | None,
        message: str,
        details: dict[str, object],
        checks: tuple[DiagnosticCheck, ...],
        events: list[WorkflowEvent],
        started_at: str,
        started: float,
    ) -> WorkflowResult:
        artifact_path = self.paths.artifact_path(run_id)
        artifact_display_path = self.paths.artifact_display_path(run_id)
        events.append(
            self._event(
                run_id=run_id,
                workflow=workflow,
                stage="artifact_persisted",
                status=CheckStatus.PASS,
                message="Workflow artifact persisted.",
                details={"path": artifact_display_path},
            )
        )
        events.append(
            self._event(
                run_id=run_id,
                workflow=workflow,
                stage="workflow_completed",
                status=CheckStatus.PASS if status == "ok" else CheckStatus.FAIL,
                message=message,
                details={"status": status, "error_code": error_code or ""},
            )
        )
        return WorkflowResult(
            run_id=run_id,
            workflow=workflow,
            status=status,
            error_code=error_code,
            error_category=error_category,
            message=message,
            started_at=started_at,
            details=details,
            checks=checks,
            events=tuple(events),
            artifact=self.artifact_store.write(
                ArtifactRecord(
                    run_id=run_id,
                    workflow=workflow,
                    created_at=self.clock(),
                    path=str(artifact_path),
                    result={
                        "run_id": run_id,
                        "workflow": workflow,
                        "status": status,
                        "error_code": error_code,
                        "error_category": error_category.value
                        if error_category
                        else None,
                        "message": message,
                        "started_at": started_at,
                        "details": details,
                        "checks": [check.as_dict() for check in checks],
                        "duration_seconds": round(current_time() - started, 3),
                    },
                    events=tuple(event.as_dict() for event in events),
                )
            ),
            duration_seconds=current_time() - started,
        )

    def _event(
        self,
        *,
        run_id: str,
        workflow: str,
        stage: str,
        status: CheckStatus,
        message: str,
        details: dict[str, object] | None = None,
    ) -> WorkflowEvent:
        return WorkflowEvent(
            run_id=run_id,
            workflow=workflow,
            stage=stage,
            status=status,
            message=message,
            timestamp=self.clock(),
            details=details or {},
        )

    def _classify_error(self, error_code: str | None) -> ErrorCategory | None:
        if error_code is None:
            return None
        if error_code in {
            "unsupported_environment",
            "missing_uv",
            "missing_git",
            "missing_auto_bean_on_path",
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
        artifact_store=WorkflowArtifactStore(),
    )
