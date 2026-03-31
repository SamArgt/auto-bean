from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from pytest import CaptureFixture, MonkeyPatch

from auto_bean.application.setup import SetupService
from auto_bean.cli.main import main
from auto_bean.domain.setup import (
    ArtifactRecord,
    CommandResult,
    EnvironmentInfo,
    ErrorCategory,
    WorkflowArtifact,
    WorkflowResult,
)
from auto_bean.infrastructure.setup import ProjectPaths


@dataclass
class FakePlatformProbe:
    environment: EnvironmentInfo

    def inspect(self) -> EnvironmentInfo:
        return self.environment


@dataclass
class FakeToolProbe:
    available_tools: dict[str, str]

    def find(self, command: str) -> str | None:
        return self.available_tools.get(command)


@dataclass
class FakeCommandRunner:
    responses: dict[tuple[str, ...], CommandResult]
    calls: list[tuple[str, ...]] = field(default_factory=list)

    def run(self, args: Sequence[str], cwd: Path | None = None) -> CommandResult:
        self.calls.append(tuple(args))
        return self.responses.get(tuple(args), CommandResult(returncode=0))


@dataclass
class FakeArtifactStore:
    records: list[ArtifactRecord] = field(default_factory=list)

    def write(self, artifact: ArtifactRecord) -> WorkflowArtifact:
        self.records.append(artifact)
        return WorkflowArtifact(
            artifact_type="workflow-run",
            path=f".auto-bean/artifacts/{artifact.run_id}.json",
        )


def make_service(
    tmp_path: Path,
    *,
    system: str = "Darwin",
    tools: dict[str, str] | None = None,
    responses: dict[tuple[str, ...], CommandResult] | None = None,
) -> tuple[SetupService, FakeArtifactStore, FakeCommandRunner]:
    repo_root = tmp_path
    (repo_root / "src").mkdir()
    (repo_root / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "auto-bean"',
                'version = "0.1.0"',
                "",
            ]
        ),
        encoding="utf-8",
    )

    artifact_store = FakeArtifactStore()
    command_runner = FakeCommandRunner(responses if responses is not None else {})
    service = SetupService(
        paths=ProjectPaths(start=repo_root),
        platform_probe=FakePlatformProbe(
            EnvironmentInfo(
                system=system,
                release="24.0.0",
                machine="arm64",
                python_version="3.13.0",
            )
        ),
        tool_probe=FakeToolProbe(
            tools
            if tools is not None
            else {
                "uv": "/opt/homebrew/bin/uv",
                "auto-bean": "/tmp/fake-auto-bean",
            }
        ),
        command_runner=command_runner,
        artifact_store=artifact_store,
        run_id_factory=lambda: "run-fixed-001",
        clock=lambda: "2026-03-31T10:30:00+02:00",
    )
    return service, artifact_store, command_runner


def test_readiness_emits_structured_run_metadata_and_artifact(tmp_path: Path) -> None:
    service, artifact_store, _ = make_service(
        tmp_path,
        responses={
            ("/tmp/fake-auto-bean", "--help"): CommandResult(returncode=0, stdout="help"),
        },
    )

    result = service.readiness()

    assert result.status == "ok"
    assert result.run_id == "run-fixed-001"
    assert result.workflow == "readiness"
    assert result.error_category is None
    assert result.artifact is not None
    assert result.artifact.path == ".auto-bean/artifacts/run-fixed-001.json"
    assert [event.stage for event in result.events] == [
        "workflow_started",
        "supported_environment",
        "uv_available",
        "auto_bean_on_path",
        "artifact_persisted",
        "workflow_completed",
    ]
    assert all(event.run_id == "run-fixed-001" for event in result.events)
    assert artifact_store.records[0].result["status"] == "ok"


def test_readiness_classifies_prerequisite_failure_and_persists_artifact(tmp_path: Path) -> None:
    service, artifact_store, _ = make_service(tmp_path, tools={})

    result = service.readiness()

    assert result.status == "failed"
    assert result.error_code == "missing_uv"
    assert result.error_category is ErrorCategory.PREREQUISITE_FAILURE
    assert result.artifact is not None
    assert artifact_store.records[0].result["error_category"] == "prerequisite_failure"
    assert artifact_store.records[0].events[-1]["stage"] == "workflow_completed"


def test_init_classifies_blocked_mutation_and_persists_artifact(tmp_path: Path) -> None:
    service, artifact_store, _ = make_service(tmp_path)

    result = service.init("demo-ledger")

    assert result.status == "failed"
    assert result.error_code == "init_not_implemented"
    assert result.error_category is ErrorCategory.BLOCKED_UNSAFE_MUTATION
    assert result.artifact is not None
    details = artifact_store.records[0].result["details"]
    assert isinstance(details, dict)
    assert details["project_name"] == "demo-ledger"


def test_cli_json_output_includes_structured_diagnostics(
    capsys: CaptureFixture[str],
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    service, _, _ = make_service(
        tmp_path,
        responses={
            ("/tmp/fake-auto-bean", "--help"): CommandResult(returncode=0, stdout="help"),
        },
    )
    monkeypatch.setattr("auto_bean.cli.main.build_setup_service", lambda: service)

    exit_code = main(["readiness", "--json"])

    payload = cast(dict[str, Any], json.loads(capsys.readouterr().out))
    assert exit_code == 0
    assert payload["run_id"] == "run-fixed-001"
    artifact = cast(dict[str, Any], payload["artifact"])
    events = cast(list[dict[str, Any]], payload["events"])
    assert artifact["path"] == ".auto-bean/artifacts/run-fixed-001.json"
    assert events[0]["stage"] == "workflow_started"


def test_cli_human_output_is_driven_by_structured_result(
    capsys: CaptureFixture[str],
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    service, _, _ = make_service(tmp_path, tools={})
    monkeypatch.setattr("auto_bean.cli.main.build_setup_service", lambda: service)

    exit_code = main(["readiness"])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "run_id: run-fixed-001" in output
    assert "artifact_path: .auto-bean/artifacts/run-fixed-001.json" in output
    assert "[FAIL] uv_available" in output


def test_cli_reports_unexpected_execution_errors_as_structured_output(
    capsys: CaptureFixture[str],
    monkeypatch: MonkeyPatch,
) -> None:
    class ExplodingService:
        def readiness(self) -> WorkflowResult:
            raise RuntimeError("boom")

        def init(self, project_name: str) -> WorkflowResult:
            raise RuntimeError(project_name)

        def execution_error(
            self,
            workflow: str,
            *,
            details: dict[str, str],
            message: str = "Workflow execution failed unexpectedly.",
        ) -> WorkflowResult:
            return WorkflowResult(
                run_id="execution-error-001",
                workflow=workflow,
                status="failed",
                error_code="execution_error",
                error_category=ErrorCategory.EXECUTION_ERROR,
                message=message,
                started_at="2026-03-31T10:30:00+02:00",
                details=details,
                artifact=WorkflowArtifact(
                    artifact_type="workflow-run",
                    path=".auto-bean/artifacts/execution-error-001.json",
                ),
            )

    monkeypatch.setattr(
        "auto_bean.cli.main.build_setup_service",
        lambda: ExplodingService(),
    )

    exit_code = main(["readiness", "--json"])

    payload = cast(dict[str, Any], json.loads(capsys.readouterr().out))
    assert exit_code == 1
    assert payload["error_code"] == "execution_error"
    assert payload["error_category"] == "execution_error"
    assert payload["details"]["exception_type"] == "RuntimeError"
    assert payload["details"]["exception_message"] == "boom"
