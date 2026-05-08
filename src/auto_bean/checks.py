from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from auto_bean.environment import CommandRunner, PlatformProbe, ToolProbe
from auto_bean.models import CheckStatus, DiagnosticCheck
from auto_bean.paths import looks_like_path, sanitize_project_name


class WorkspaceChecks:
    def check_environment(self) -> DiagnosticCheck:
        environment = PlatformProbe().inspect()
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

    def check_target(
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

    def check_update_target(self, target_directory: Path) -> DiagnosticCheck:
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
            for path in (
                "AGENTS.md",
                ".agents/skills",
                "ledger.beancount",
                ".auto-bean/memory",
            )
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

    def check_update_assets(
        self, template_directory: Path, skill_sources_directory: Path
    ) -> DiagnosticCheck:
        missing = [
            str(path)
            for path in (
                template_directory / "README.md",
                template_directory / "AGENTS.md",
                template_directory / ".auto-bean" / "memory" / "MEMORY.md",
                template_directory / "scripts" / "install-dependencies.sh",
                template_directory / "scripts" / "open-fava.sh",
                template_directory / "scripts" / "validate-ledger.sh",
                skill_sources_directory / "auto-bean-categorize" / "SKILL.md",
                skill_sources_directory / "auto-bean-query" / "SKILL.md",
                skill_sources_directory / "auto-bean-write" / "SKILL.md",
                skill_sources_directory / "auto-bean-import" / "SKILL.md",
                skill_sources_directory / "auto-bean-process" / "SKILL.md",
                skill_sources_directory / "auto-bean-memory" / "SKILL.md",
                skill_sources_directory / "shared" / "workflow-rules.md",
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

    def check_coding_agent(self, coding_agent: str) -> DiagnosticCheck:
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

    def check_required_assets(
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

    def check_tool(
        self,
        command: str,
        *,
        name: str,
        message: str,
        error_code: str,
        failure_message: str,
        remediation: str,
    ) -> DiagnosticCheck:
        path = ToolProbe().find(command)
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

    def bootstrap_workspace_runtime(self, target_directory: Path) -> DiagnosticCheck:
        uv_path = ToolProbe().find("uv")
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
        install_command = ["./scripts/install-dependencies.sh"]
        install_result = CommandRunner().run(install_command, cwd=target_directory)
        if install_result.returncode != 0:
            return DiagnosticCheck(
                name="workspace_runtime_bootstrapped",
                status=CheckStatus.FAIL,
                error_code="workspace_runtime_bootstrap_failed",
                message="Failed to install the workspace runtime dependencies.",
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
                "bootstrap_commands": [" ".join(install_command)],
                "uv_path": uv_path,
            },
        )

    def bean_check_command(self, target_directory: Path) -> list[str]:
        return [
            str(target_directory / ".venv" / "bin" / "bean-check"),
            str(target_directory / "ledger.beancount"),
        ]

    def run_workspace_command_check(
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
        result = CommandRunner().run(command, cwd=cwd)
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

    def validate_generated_ledger(self, target_directory: Path) -> DiagnosticCheck:
        command = self.bean_check_command(target_directory)
        return self.run_workspace_command_check(
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

    def check_workspace_fava_available(self, target_directory: Path) -> DiagnosticCheck:
        command = [str(target_directory / ".venv" / "bin" / "fava"), "--version"]
        return self.run_workspace_command_check(
            command=command,
            cwd=target_directory,
            name="workspace_fava_available",
            success_message="Fava is runnable from the workspace runtime.",
            error_code="workspace_fava_unavailable",
            failure_message="Fava is not runnable from the workspace runtime.",
            detail_key="fava_command",
        )

    def check_workspace_docling_available(
        self, target_directory: Path
    ) -> DiagnosticCheck:
        command = [str(target_directory / ".venv" / "bin" / "docling"), "--version"]
        return self.run_workspace_command_check(
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

    def create_initial_git_commit(
        self, target_directory: Path, git_path: str
    ) -> DiagnosticCheck:
        add_command = [git_path, "add", "-A"]
        add_result = CommandRunner().run(add_command, cwd=target_directory)
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
        commit_result = CommandRunner().run(commit_command, cwd=target_directory)
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

    def run_command_check(
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
        result = CommandRunner().run(resolved_command, cwd=cwd)
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
