from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

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
    ProjectPaths,
    ToolLocator,
    ToolProbe,
    current_time,
    current_timestamp,
    generate_run_id,
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
        events.append(
            self._event(
                run_id=run_id,
                workflow="init",
                stage=check.name,
                status=check.status,
                message=check.message,
                details=check.details,
            )
        )
        return self._result(
            run_id=run_id,
            workflow="init",
            status="failed",
            error_code=check.error_code,
            error_category=self._classify_error(check.error_code),
            message=check.message,
            details=check.details,
            checks=(check,),
            events=events,
            started_at=started_at,
            started=started,
        )

    def execution_error(
        self,
        workflow: str,
        *,
        details: dict[str, str],
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

    def _result(
        self,
        *,
        run_id: str,
        workflow: str,
        status: str,
        error_code: str | None,
        error_category: ErrorCategory | None,
        message: str,
        details: dict[str, str],
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
                        "error_category": error_category.value if error_category else None,
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
        details: dict[str, str] | None = None,
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
            "missing_auto_bean_on_path",
        }:
            return ErrorCategory.PREREQUISITE_FAILURE
        if error_code == "init_not_implemented":
            return ErrorCategory.BLOCKED_UNSAFE_MUTATION
        return ErrorCategory.EXECUTION_ERROR


def build_setup_service(start: Path | None = None) -> SetupService:
    return SetupService(
        paths=ProjectPaths(start=start),
        platform_probe=PlatformProbe(),
        tool_probe=ToolProbe(),
        command_runner=CommandRunner(),
        artifact_store=WorkflowArtifactStore(),
    )
