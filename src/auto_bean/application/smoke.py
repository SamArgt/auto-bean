from __future__ import annotations

import io
import json
from collections.abc import Sequence
from contextlib import redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from auto_bean.application.setup import SetupService
from auto_bean.cli.main import main
from auto_bean.domain.setup import ArtifactRecord, CommandResult, EnvironmentInfo, WorkflowArtifact
from auto_bean.infrastructure.setup import ProjectPaths


@dataclass
class _FakePlatformProbe:
    environment: EnvironmentInfo

    def inspect(self) -> EnvironmentInfo:
        return self.environment


@dataclass
class _FakeToolProbe:
    available_tools: dict[str, str]

    def find(self, command: str) -> str | None:
        return self.available_tools.get(command)


@dataclass
class _FakeCommandRunner:
    responses: dict[tuple[str, ...], CommandResult]

    def run(self, args: Sequence[str], cwd: Path | None = None) -> CommandResult:
        if cwd is not None and tuple(args[:2]) == ("/usr/bin/git", "init"):
            (cwd / ".git").mkdir(parents=True, exist_ok=True)
        if cwd is not None and tuple(args[:2]) == ("/opt/homebrew/bin/uv", "venv"):
            (cwd / ".venv" / "bin").mkdir(parents=True, exist_ok=True)
            (cwd / ".venv" / "bin" / "python").write_text("", encoding="utf-8")
        if cwd is not None and tuple(args[:3]) == ("/opt/homebrew/bin/uv", "pip", "install"):
            (cwd / ".venv" / "bin").mkdir(parents=True, exist_ok=True)
            (cwd / ".venv" / "bin" / "bean-check").write_text("", encoding="utf-8")
            (cwd / ".venv" / "bin" / "fava").write_text("", encoding="utf-8")
        return self.responses.get(tuple(args), CommandResult(returncode=0))


@dataclass
class _ArtifactStore:
    records: list[ArtifactRecord] = field(default_factory=list)

    def write(self, artifact: ArtifactRecord) -> WorkflowArtifact:
        self.records.append(artifact)
        artifact_path = Path(artifact.path)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            json.dumps(
                {
                    "run_id": artifact.run_id,
                    "workflow": artifact.workflow,
                    "created_at": artifact.created_at,
                    "result": dict(artifact.result),
                    "events": list(artifact.events),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return WorkflowArtifact(
            artifact_type="workflow-run",
            path=str(artifact_path.relative_to(artifact_path.parents[2])),
        )


def _build_service(repo_root: Path, run_id: str, *, readiness_success: bool) -> SetupService:
    tools = {"uv": "/opt/homebrew/bin/uv", "git": "/usr/bin/git"}
    responses: dict[tuple[str, ...], CommandResult] = {}
    if readiness_success:
        tools["auto-bean"] = "/tmp/fake-auto-bean"
        responses[("/tmp/fake-auto-bean", "--help")] = CommandResult(
            returncode=0,
            stdout="help",
        )

    return SetupService(
        paths=ProjectPaths(start=repo_root),
        platform_probe=_FakePlatformProbe(
            EnvironmentInfo(
                system="Darwin",
                release="24.0.0",
                machine="arm64",
                python_version="3.13.0",
            )
        ),
        tool_probe=_FakeToolProbe(tools),
        command_runner=_FakeCommandRunner(responses),
        artifact_store=_ArtifactStore(),
        run_id_factory=lambda: run_id,
        clock=lambda: "2026-03-31T10:45:00+02:00",
        prompt=lambda _: "Codex",
    )


def run_smoke_checks() -> int:
    with TemporaryDirectory() as tmp_dir:
        repo_root = Path(tmp_dir)
        (repo_root / "src").mkdir()
        (repo_root / "pyproject.toml").write_text(
            "[project]\nname = 'auto-bean'\nversion = '0.1.0'\n",
            encoding="utf-8",
        )
        template_root = repo_root / "workspace_template"
        (template_root / "beancount").mkdir(parents=True)
        (template_root / "docs").mkdir(parents=True)
        (template_root / ".agents" / "skills").mkdir(parents=True)
        (template_root / "statements" / "raw").mkdir(parents=True)
        (template_root / ".auto-bean").mkdir(parents=True)
        (template_root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
        (template_root / "ledger.beancount").write_text(
            'option "title" "Smoke Ledger"\ninclude "beancount/opening-balances.beancount"\n',
            encoding="utf-8",
        )
        (template_root / "beancount" / "opening-balances.beancount").write_text(
            '1970-01-01 open Assets:Checking EUR\n1970-01-01 open Equity:Opening-Balances EUR\n',
            encoding="utf-8",
        )
        (template_root / "docs" / "README.md").write_text("# Docs\n", encoding="utf-8")
        (template_root / ".agents" / "skills" / "README.md").write_text(
            "# Skills\n",
            encoding="utf-8",
        )
        project_name = f"demo-ledger-{repo_root.name}"

        cases = (
            ("readiness-success", ["readiness", "--json"], _build_service(repo_root, "smoke-readiness", readiness_success=True), 0),
            ("init-success", ["init", project_name, "--json"], _build_service(repo_root, "smoke-init", readiness_success=False), 0),
            ("init-blocked", ["init", "bad/name", "--json"], _build_service(repo_root, "smoke-init-blocked", readiness_success=False), 1),
        )

        results: list[dict[str, object]] = []
        for name, argv, service, expected_exit in cases:
            buffer = io.StringIO()
            with patch("auto_bean.cli.main.build_setup_service", lambda: service):
                with redirect_stdout(buffer):
                    exit_code = main(argv)
            payload = json.loads(buffer.getvalue())
            results.append(
                {
                    "name": name,
                    "exit_code": exit_code,
                    "expected_exit": expected_exit,
                    "status": payload["status"],
                    "error_code": payload["error_code"],
                    "artifact": payload["artifact"]["path"] if payload["artifact"] else None,
                }
            )

        if any(item["exit_code"] != item["expected_exit"] for item in results):
            print(json.dumps({"status": "failed", "results": results}, indent=2, sort_keys=True))
            return 1

        print(json.dumps({"status": "ok", "results": results}, indent=2, sort_keys=True))
        return 0
