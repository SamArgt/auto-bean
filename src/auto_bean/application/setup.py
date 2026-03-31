from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from auto_bean.domain.setup import CheckStatus, DiagnosticCheck, WorkflowResult
from auto_bean.infrastructure.setup import (
    CommandRunner,
    PlatformProbe,
    ProjectPaths,
    ToolProbe,
    current_time,
)


@dataclass
class SetupService:
    paths: ProjectPaths
    platform_probe: PlatformProbe
    tool_probe: ToolProbe
    command_runner: CommandRunner

    def readiness(self) -> WorkflowResult:
        started = current_time()
        checks = (
            self._check_supported_environment(),
            self._check_uv_available(),
            self._check_auto_bean_on_path(),
        )
        failed_check = next(
            (check for check in checks if check.status is CheckStatus.FAIL),
            None,
        )
        if failed_check is not None:
            return self._result(
                status="failed",
                error_code=failed_check.error_code,
                message=failed_check.message,
                details=failed_check.details,
                checks=checks,
                started=started,
            )

        warned_check = next(
            (check for check in checks if check.status is CheckStatus.WARN),
            None,
        )
        if warned_check is not None:
            return self._result(
                status="failed",
                error_code=warned_check.error_code,
                message=warned_check.message,
                details=warned_check.details,
                checks=checks,
                started=started,
            )

        return self._result(
            status="ok",
            error_code=None,
            message="Readiness check passed. auto-bean is installed and discoverable.",
            details={"command": "auto-bean --help"},
            checks=checks,
            started=started,
        )

    def init(self, project_name: str) -> WorkflowResult:
        started = current_time()
        check = DiagnosticCheck(
            name="workspace_init",
            status=CheckStatus.WARN,
            error_code="init_not_implemented",
            message=(
                "Workspace scaffolding is not implemented yet. A later story will add "
                "'auto-bean init <PROJECT-NAME>'."
            ),
            details={"project_name": project_name},
        )
        return self._result(
            status="failed",
            error_code=check.error_code,
            message=check.message,
            details=check.details,
            checks=(check,),
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

    def _result(
        self,
        *,
        status: str,
        error_code: str | None,
        message: str,
        details: dict[str, str],
        checks: tuple[DiagnosticCheck, ...],
        started: float,
    ) -> WorkflowResult:
        return WorkflowResult(
            status=status,
            error_code=error_code,
            message=message,
            details=details,
            checks=checks,
            duration_seconds=current_time() - started,
        )


def build_setup_service(start: Path | None = None) -> SetupService:
    return SetupService(
        paths=ProjectPaths(start=start),
        platform_probe=PlatformProbe(),
        tool_probe=ToolProbe(),
        command_runner=CommandRunner(),
    )
