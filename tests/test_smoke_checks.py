from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

from pytest import CaptureFixture

from auto_bean.application.setup import SetupService
from auto_bean.application.smoke import run_smoke_checks
from auto_bean.domain.setup import CommandResult, EnvironmentInfo
from auto_bean.infrastructure.setup import ProjectPaths, WorkflowArtifactStore


class _PlatformProbe:
    def inspect(self) -> EnvironmentInfo:
        return EnvironmentInfo(
            system="Darwin",
            release="24.0.0",
            machine="arm64",
            python_version="3.13.0",
        )


class _ToolProbe:
    def find(self, command: str) -> str | None:
        if command == "uv":
            return "/opt/homebrew/bin/uv"
        if command == "auto-bean":
            return "/tmp/fake-auto-bean"
        return None


class _CommandRunner:
    def run(self, args: Sequence[str], cwd: Path | None = None) -> CommandResult:
        return CommandResult(returncode=0, stdout="help")


def test_workflow_artifact_store_writes_governed_json_artifact(tmp_path: Path) -> None:
    repo_root = tmp_path
    (repo_root / "src").mkdir()
    (repo_root / "pyproject.toml").write_text(
        "[project]\nname = 'auto-bean'\nversion = '0.1.0'\n",
        encoding="utf-8",
    )
    service = SetupService(
        paths=ProjectPaths(start=repo_root),
        platform_probe=_PlatformProbe(),
        tool_probe=_ToolProbe(),
        command_runner=_CommandRunner(),
        artifact_store=WorkflowArtifactStore(),
        run_id_factory=lambda: "artifact-store-001",
        clock=lambda: "2026-03-31T10:50:00+02:00",
    )

    result = service.readiness()

    artifact_path = repo_root / ".auto-bean" / "artifacts" / "artifact-store-001.json"
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert result.artifact is not None
    assert result.artifact.path == ".auto-bean/artifacts/artifact-store-001.json"
    assert payload["result"]["status"] == "ok"
    assert payload["events"][0]["stage"] == "workflow_started"


def test_workflow_artifact_store_falls_back_to_current_directory_outside_repo(
    tmp_path: Path,
) -> None:
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    service = SetupService(
        paths=ProjectPaths(start=outside_dir),
        platform_probe=_PlatformProbe(),
        tool_probe=_ToolProbe(),
        command_runner=_CommandRunner(),
        artifact_store=WorkflowArtifactStore(),
        run_id_factory=lambda: "artifact-outside-001",
        clock=lambda: "2026-03-31T10:50:00+02:00",
    )

    result = service.readiness()

    artifact_path = outside_dir / ".auto-bean" / "artifacts" / "artifact-outside-001.json"
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert result.status == "ok"
    assert result.artifact is not None
    assert result.artifact.path == ".auto-bean/artifacts/artifact-outside-001.json"
    assert payload["result"]["status"] == "ok"


def test_run_smoke_checks_covers_success_and_blocked_paths(capsys: CaptureFixture[str]) -> None:
    exit_code = run_smoke_checks()

    payload = cast(dict[str, Any], json.loads(capsys.readouterr().out))
    results = cast(list[dict[str, Any]], payload["results"])
    assert exit_code == 0
    assert payload["status"] == "ok"
    assert [result["name"] for result in results] == [
        "readiness-success",
        "init-success",
        "init-blocked",
    ]
    assert results[1]["error_code"] is None
    assert results[2]["error_code"] == "unsafe_project_name"
