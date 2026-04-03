from __future__ import annotations

import json
from collections.abc import Callable, Sequence
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
        if cwd is not None and tuple(args[:2]) == ("/usr/bin/git", "init"):
            (cwd / ".git").mkdir(parents=True, exist_ok=True)
        if cwd is not None and tuple(args[:2]) == ("/opt/homebrew/bin/uv", "venv"):
            (cwd / ".venv" / "bin").mkdir(parents=True, exist_ok=True)
            (cwd / ".venv" / "bin" / "python").write_text("", encoding="utf-8")
        if cwd is not None and tuple(args[:3]) == (
            "/opt/homebrew/bin/uv",
            "pip",
            "install",
        ):
            (cwd / ".venv" / "bin").mkdir(parents=True, exist_ok=True)
            (cwd / ".venv" / "bin" / "bean-check").write_text("", encoding="utf-8")
            (cwd / ".venv" / "bin" / "fava").write_text("", encoding="utf-8")
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


def seed_workspace_template(repo_root: Path) -> None:
    template_root = repo_root / "workspace_template"
    (template_root / "beancount").mkdir(parents=True)
    (template_root / ".agents").mkdir(parents=True)
    (template_root / "statements" / "raw").mkdir(parents=True)
    (template_root / ".auto-bean" / "artifacts").mkdir(parents=True)
    (template_root / ".auto-bean" / "proposals").mkdir(parents=True)
    (template_root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    (template_root / "ledger.beancount").write_text(
        'option "title" "Test Ledger"\ninclude "beancount/opening-balances.beancount"\n',
        encoding="utf-8",
    )
    (template_root / "beancount" / "opening-balances.beancount").write_text(
        "1970-01-01 open Assets:Checking EUR\n1970-01-01 open Equity:Opening-Balances EUR\n",
        encoding="utf-8",
    )
    (template_root / ".auto-bean" / "artifacts" / ".gitkeep").write_text(
        "", encoding="utf-8"
    )
    (template_root / ".auto-bean" / "proposals" / ".gitkeep").write_text(
        "", encoding="utf-8"
    )
    (template_root / "statements" / "raw" / ".gitkeep").write_text("", encoding="utf-8")

    skill_sources_root = repo_root / "skill_sources"
    (skill_sources_root / "auto-bean-apply" / "scripts").mkdir(parents=True)
    (skill_sources_root / "auto-bean-apply" / "agents").mkdir(parents=True)
    (skill_sources_root / "shared").mkdir(parents=True)
    (skill_sources_root / "auto-bean-apply" / "SKILL.md").write_text(
        "# Apply\n", encoding="utf-8"
    )
    (skill_sources_root / "auto-bean-apply" / "agents" / "openai.yaml").write_text(
        'interface:\n  display_name: "Apply"\n  short_description: "Apply changes"\n  default_prompt: "Use $auto-bean-apply."\n',
        encoding="utf-8",
    )
    (skill_sources_root / "shared" / "mutation-pipeline.md").write_text(
        "# Pipeline\n", encoding="utf-8"
    )
    (skill_sources_root / "shared" / "mutation-authority-matrix.md").write_text(
        "# Authority\n", encoding="utf-8"
    )


def make_service(
    tmp_path: Path,
    *,
    system: str = "Darwin",
    tools: dict[str, str] | None = None,
    responses: dict[tuple[str, ...], CommandResult] | None = None,
    prompt: Callable[[str], str] | None = None,
) -> tuple[SetupService, FakeArtifactStore, FakeCommandRunner]:
    repo_root = tmp_path
    (repo_root / "src").mkdir(exist_ok=True)
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
                "git": "/usr/bin/git",
                "uv": "/opt/homebrew/bin/uv",
                "auto-bean": "/tmp/fake-auto-bean",
            }
        ),
        command_runner=command_runner,
        artifact_store=artifact_store,
        run_id_factory=lambda: "run-fixed-001",
        clock=lambda: "2026-03-31T10:30:00+02:00",
        prompt=prompt or (lambda _: "Codex"),
    )
    return service, artifact_store, command_runner


def test_readiness_emits_structured_run_metadata_and_artifact(tmp_path: Path) -> None:
    service, artifact_store, _ = make_service(
        tmp_path,
        responses={
            ("/tmp/fake-auto-bean", "--help"): CommandResult(
                returncode=0, stdout="help"
            ),
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


def test_readiness_classifies_prerequisite_failure_and_persists_artifact(
    tmp_path: Path,
) -> None:
    service, artifact_store, _ = make_service(tmp_path, tools={})

    result = service.readiness()

    assert result.status == "failed"
    assert result.error_code == "missing_uv"
    assert result.error_category is ErrorCategory.PREREQUISITE_FAILURE
    assert result.artifact is not None
    assert artifact_store.records[0].result["error_category"] == "prerequisite_failure"
    assert artifact_store.records[0].events[-1]["stage"] == "workflow_completed"


def test_init_creates_workspace_and_persists_created_manifest(tmp_path: Path) -> None:
    seed_workspace_template(tmp_path)
    project_name = f"demo-ledger-{tmp_path.name[-6:]}"
    service, artifact_store, _ = make_service(tmp_path)

    result = service.init(project_name)

    workspace_root = tmp_path.parent / project_name
    assert result.status == "ok"
    assert result.error_code is None
    assert result.error_category is None
    assert result.artifact is not None
    assert workspace_root.joinpath("ledger.beancount").is_file()
    assert workspace_root.joinpath("AGENTS.md").is_file()
    assert workspace_root.joinpath(
        ".agents", "skills", "auto-bean-apply", "SKILL.md"
    ).is_file()
    assert workspace_root.joinpath(
        ".agents", "skills", "shared", "mutation-pipeline.md"
    ).is_file()
    assert workspace_root.joinpath(".git").is_dir()
    assert workspace_root.joinpath(".gitignore").is_file()
    assert workspace_root.joinpath("scripts", "validate-ledger.sh").is_file()
    assert workspace_root.joinpath(".venv", "bin", "bean-check").is_file()
    assert workspace_root.joinpath(".venv", "bin", "fava").is_file()
    details = artifact_store.records[0].result["details"]
    assert isinstance(details, dict)
    assert details["project_name"] == project_name
    assert details["coding_agent"] == "Codex"
    created_paths = cast(list[str], details["created_paths"])
    assert ".gitignore" in created_paths
    assert "ledger.beancount" in created_paths
    assert "AGENTS.md" in created_paths
    assert ".agents/skills/auto-bean-apply/SKILL.md" in created_paths
    assert "scripts/validate-ledger.sh" in created_paths
    assert "scripts/open-fava.sh" in created_paths
    next_steps = cast(list[str], details["next_steps"])
    assert (
        "Review AGENTS.md for the Codex-first workspace workflow and path guide."
        in next_steps
    )


def test_init_creates_initial_git_commit(tmp_path: Path) -> None:
    seed_workspace_template(tmp_path)
    project_name = f"git-commit-{tmp_path.name[-6:]}"
    service, _, command_runner = make_service(tmp_path)

    result = service.init(project_name)

    workspace_root = tmp_path.parent / project_name
    assert result.status == "ok"
    assert ("/usr/bin/git", "init") in command_runner.calls
    assert ("/usr/bin/git", "add", "-A") in command_runner.calls
    assert (
        "/usr/bin/git",
        "commit",
        "-m",
        "Initial workspace scaffold",
    ) in command_runner.calls
    assert workspace_root.joinpath(".venv").is_dir()


def test_project_paths_uses_installed_resources_fallback(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='auto-bean'\nversion='0.1.0'\n", encoding="utf-8"
    )
    monkeypatch.setattr(
        ProjectPaths,
        "installed_resources_directory",
        property(lambda self: tmp_path / "installed-root"),
    )
    installed_root = tmp_path / "installed-root"
    (installed_root / "workspace_template").mkdir(parents=True)
    (installed_root / "skill_sources").mkdir(parents=True)

    paths = ProjectPaths(start=tmp_path)

    assert paths.workspace_template_directory == installed_root / "workspace_template"
    assert paths.skill_sources_directory == installed_root / "skill_sources"


def test_init_rejects_unsupported_coding_agent(tmp_path: Path) -> None:
    seed_workspace_template(tmp_path)
    project_name = f"unsupported-agent-{tmp_path.name[-6:]}"
    service, _, _ = make_service(tmp_path, prompt=lambda _: "Claude")

    result = service.init(project_name)

    assert result.status == "failed"
    assert result.error_code == "unsupported_coding_agent"
    assert result.error_category is ErrorCategory.VALIDATION_FAILURE


def test_init_rejects_unsafe_project_name(tmp_path: Path) -> None:
    seed_workspace_template(tmp_path)
    service, _, _ = make_service(tmp_path)

    result = service.init("bad/name")

    assert result.status == "failed"
    assert result.error_code == "unsafe_project_name"
    assert result.error_category is ErrorCategory.BLOCKED_UNSAFE_MUTATION


def test_init_rejects_non_empty_target_directory(tmp_path: Path) -> None:
    seed_workspace_template(tmp_path)
    project_name = f"occupied-ledger-{tmp_path.name[-6:]}"
    workspace_root = tmp_path.parent / project_name
    workspace_root.mkdir(exist_ok=True)
    (workspace_root / "existing.txt").write_text("occupied\n", encoding="utf-8")
    service, _, _ = make_service(tmp_path)

    result = service.init(project_name)

    assert result.status == "failed"
    assert result.error_code == "non_empty_target_directory"


def test_init_rejects_missing_template_assets(tmp_path: Path) -> None:
    project_name = f"missing-template-{tmp_path.name[-6:]}"
    (tmp_path / "workspace_template").mkdir(parents=True)
    service, _, _ = make_service(tmp_path)

    result = service.init(project_name)

    assert result.status == "failed"
    assert result.error_code == "missing_template_assets"
    assert result.error_category is ErrorCategory.PREREQUISITE_FAILURE


def test_init_rejects_missing_git(tmp_path: Path) -> None:
    seed_workspace_template(tmp_path)
    project_name = f"missing-git-{tmp_path.name[-6:]}"
    service, _, _ = make_service(
        tmp_path,
        tools={
            "uv": "/opt/homebrew/bin/uv",
            "auto-bean": "/tmp/fake-auto-bean",
        },
    )

    result = service.init(project_name)

    assert result.status == "failed"
    assert result.error_code == "missing_git"
    assert result.error_category is ErrorCategory.PREREQUISITE_FAILURE
    assert not (tmp_path.parent / project_name).exists()


def test_init_rejects_when_initial_git_commit_fails(tmp_path: Path) -> None:
    seed_workspace_template(tmp_path)
    project_name = f"git-commit-fail-{tmp_path.name[-6:]}"
    workspace_root = tmp_path.parent / project_name
    service, _, _ = make_service(
        tmp_path,
        responses={
            (
                "/usr/bin/git",
                "commit",
                "-m",
                "Initial workspace scaffold",
            ): CommandResult(returncode=1, stderr="author identity unknown"),
        },
    )

    result = service.init(project_name)

    assert result.status == "failed"
    assert result.error_code == "workspace_git_commit_failed"
    assert result.error_category is ErrorCategory.PREREQUISITE_FAILURE
    assert not workspace_root.exists()


def test_init_rejects_workspace_runtime_bootstrap_failure(tmp_path: Path) -> None:
    seed_workspace_template(tmp_path)
    project_name = f"bootstrap-failure-{tmp_path.name[-6:]}"
    service, _, _ = make_service(
        tmp_path,
        responses={
            (
                "/opt/homebrew/bin/uv",
                "pip",
                "install",
                "--python",
                str(tmp_path.parent / project_name / ".venv" / "bin" / "python"),
                "beancount",
                "fava",
            ): CommandResult(returncode=1, stderr="network error"),
        },
    )

    result = service.init(project_name)

    assert result.status == "failed"
    assert result.error_code == "workspace_runtime_bootstrap_failed"
    assert result.error_category is ErrorCategory.PREREQUISITE_FAILURE
    assert result.details["validation_status"] == "blocked"
    assert not (tmp_path.parent / project_name).exists()


def test_init_rejects_when_workspace_fava_is_not_runnable(tmp_path: Path) -> None:
    seed_workspace_template(tmp_path)
    project_name = f"missing-fava-{tmp_path.name[-6:]}"
    workspace_root = tmp_path.parent / project_name
    service, _, _ = make_service(
        tmp_path,
        responses={
            (
                str(workspace_root / ".venv" / "bin" / "fava"),
                "--version",
            ): CommandResult(
                returncode=1,
                stderr="missing fava",
            ),
        },
    )

    result = service.init(project_name)

    assert result.status == "failed"
    assert result.error_code == "workspace_fava_unavailable"
    assert result.error_category is ErrorCategory.VALIDATION_FAILURE
    assert not workspace_root.exists()


def test_cli_json_output_includes_structured_diagnostics(
    capsys: CaptureFixture[str],
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_workspace_template(tmp_path)
    service, _, _ = make_service(
        tmp_path,
        responses={
            ("/tmp/fake-auto-bean", "--help"): CommandResult(
                returncode=0, stdout="help"
            ),
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


def test_cli_init_human_output_lists_created_files_and_next_steps(
    capsys: CaptureFixture[str],
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_workspace_template(tmp_path)
    project_name = f"cli-ledger-{tmp_path.name[-6:]}"
    service, _, _ = make_service(tmp_path)
    monkeypatch.setattr("auto_bean.cli.main.build_setup_service", lambda: service)

    exit_code = main(["init", project_name])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert f"project_name: {project_name}" in output
    assert "coding_agent: Codex" in output
    assert "created_paths:" in output
    assert "next_steps:" in output
    assert "Review AGENTS.md for the Codex-first workspace workflow and path guide." in output


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
                details=cast(dict[str, object], details),
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
