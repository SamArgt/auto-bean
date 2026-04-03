from __future__ import annotations

import io
import json
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from auto_bean.cli import main
from auto_bean.init import (
    CommandResult,
    EnvironmentInfo,
    InitService,
    ProjectPaths,
)


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

    def run(self, args: object, cwd: Path | None = None) -> CommandResult:
        command = tuple(args) if isinstance(args, (list, tuple)) else tuple()
        if cwd is not None and command[:2] == ("/usr/bin/git", "init"):
            (cwd / ".git").mkdir(parents=True, exist_ok=True)
        if cwd is not None and command[:2] == ("/opt/homebrew/bin/uv", "venv"):
            (cwd / ".venv" / "bin").mkdir(parents=True, exist_ok=True)
            (cwd / ".venv" / "bin" / "python").write_text("", encoding="utf-8")
        if cwd is not None and command[:3] == (
            "/opt/homebrew/bin/uv",
            "pip",
            "install",
        ):
            (cwd / ".venv" / "bin").mkdir(parents=True, exist_ok=True)
            (cwd / ".venv" / "bin" / "bean-check").write_text("", encoding="utf-8")
            (cwd / ".venv" / "bin" / "fava").write_text("", encoding="utf-8")
        return self.responses.get(command, CommandResult(returncode=0))


def _build_service(repo_root: Path) -> InitService:
    return InitService(
        paths=ProjectPaths(start=repo_root),
        platform=_FakePlatformProbe(
            EnvironmentInfo(
                system="Darwin",
                release="24.0.0",
                machine="arm64",
                python_version="3.13.0",
            )
        ),
        tools=_FakeToolProbe({"uv": "/opt/homebrew/bin/uv", "git": "/usr/bin/git"}),
        commands=_FakeCommandRunner({}),
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
        skill_sources_root = repo_root / "skill_sources"
        (skill_sources_root / "auto-bean-apply" / "scripts").mkdir(parents=True)
        (skill_sources_root / "auto-bean-apply" / "agents").mkdir(parents=True)
        (skill_sources_root / "shared").mkdir(parents=True)
        (skill_sources_root / "auto-bean-apply" / "SKILL.md").write_text(
            "# Apply\n",
            encoding="utf-8",
        )
        (skill_sources_root / "auto-bean-apply" / "agents" / "openai.yaml").write_text(
            'interface:\n  display_name: "Apply"\n  short_description: "Apply changes"\n  default_prompt: "Use $auto-bean-apply."\n',
            encoding="utf-8",
        )
        (skill_sources_root / "shared" / "mutation-pipeline.md").write_text(
            "# Pipeline\n",
            encoding="utf-8",
        )
        (skill_sources_root / "shared" / "mutation-authority-matrix.md").write_text(
            "# Authority\n",
            encoding="utf-8",
        )
        template_root = repo_root / "workspace_template"
        (template_root / "beancount").mkdir(parents=True)
        (template_root / "docs").mkdir(parents=True)
        (template_root / "statements" / "raw").mkdir(parents=True)
        (template_root / ".auto-bean" / "artifacts").mkdir(parents=True)
        (template_root / ".auto-bean" / "proposals").mkdir(parents=True)
        (template_root / ".agents").mkdir(parents=True)
        (template_root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
        (template_root / "ledger.beancount").write_text(
            'option "title" "Smoke Ledger"\ninclude "beancount/opening-balances.beancount"\n',
            encoding="utf-8",
        )
        (template_root / "beancount" / "opening-balances.beancount").write_text(
            "1970-01-01 open Assets:Checking EUR\n1970-01-01 open Equity:Opening-Balances EUR\n",
            encoding="utf-8",
        )
        (template_root / "docs" / "README.md").write_text("# Docs\n", encoding="utf-8")
        project_name = f"demo-ledger-{repo_root.name}"

        cases = (
            (
                "init-success",
                ["init", project_name, "--json"],
                _build_service(repo_root),
                0,
            ),
            ("init-blocked", ["init", ".", "--json"], _build_service(repo_root), 1),
        )

        results: list[dict[str, object]] = []
        for name, argv, service, expected_exit in cases:
            buffer = io.StringIO()
            with patch("auto_bean.cli.build_init_service", lambda: service):
                with patch("sys.stdout", buffer):
                    exit_code = main(argv)
            payload = json.loads(buffer.getvalue())
            results.append(
                {
                    "name": name,
                    "exit_code": exit_code,
                    "expected_exit": expected_exit,
                    "status": payload["status"],
                    "error_code": payload["error_code"],
                }
            )

        if any(item["exit_code"] != item["expected_exit"] for item in results):
            print(
                json.dumps(
                    {"status": "failed", "results": results}, indent=2, sort_keys=True
                )
            )
            return 1

        print(
            json.dumps({"status": "ok", "results": results}, indent=2, sort_keys=True)
        )
        return 0
