from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from pytest import CaptureFixture, MonkeyPatch

from auto_bean.application.setup import SetupService
from auto_bean.cli.main import main
from auto_bean.domain.setup import CommandResult, EnvironmentInfo


def test_package_foundation_layout_and_entrypoint() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    src_root = repo_root / "src" / "auto_bean"

    assert src_root.is_dir()
    assert (src_root / "__init__.py").is_file()
    assert (src_root / "__main__.py").is_file()

    for package_dir in ("cli", "application", "domain", "infrastructure", "memory"):
        assert (src_root / package_dir).is_dir()
        assert (src_root / package_dir / "__init__.py").is_file()

    from auto_bean import main as entrypoint

    assert callable(entrypoint)


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
    calls: list[tuple[str, ...]] | None = None

    def run(self, args: Sequence[str], cwd: Path | None = None) -> CommandResult:
        if self.calls is not None:
            self.calls.append(tuple(args))
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


def make_service(
    tmp_path: Path,
    *,
    system: str = "Darwin",
    tools: dict[str, str] | None = None,
    responses: dict[tuple[str, ...], CommandResult] | None = None,
    calls: list[tuple[str, ...]] | None = None,
    prompt: Callable[[str], str] | None = None,
) -> SetupService:
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

    from auto_bean.infrastructure.setup import ProjectPaths

    return SetupService(
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
            }
        ),
        command_runner=FakeCommandRunner(responses if responses is not None else {}, calls=calls),
        prompt=prompt or (lambda _: "Codex"),
    )


def test_readiness_fails_on_unsupported_os(tmp_path: Path) -> None:
    service = make_service(tmp_path, system="Linux")

    result = service.readiness()

    assert result.status == "failed"
    assert result.error_code == "unsupported_environment"
    assert result.checks[0].details["detected_system"] == "Linux"


def test_readiness_reports_missing_uv_prerequisite(tmp_path: Path) -> None:
    service = make_service(tmp_path, tools={})

    result = service.readiness()

    assert result.status == "failed"
    assert result.error_code == "missing_uv"
    remediation = result.checks[1].details["remediation"]
    assert isinstance(remediation, str)
    assert "uv tool install --from . --force auto-bean" in remediation


def test_readiness_succeeds_when_auto_bean_is_on_path(tmp_path: Path) -> None:
    auto_bean_path = tmp_path / "bin" / "auto-bean"
    auto_bean_path.parent.mkdir()
    auto_bean_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    service = make_service(
        tmp_path,
        tools={
            "uv": "/opt/homebrew/bin/uv",
            "auto-bean": str(auto_bean_path),
        },
        responses={
            (str(auto_bean_path), "--help"): CommandResult(returncode=0, stdout="help"),
        },
    )

    result = service.readiness()

    assert result.status == "ok"
    assert result.error_code is None
    assert result.duration_seconds < 120


def test_readiness_reports_when_auto_bean_is_missing_from_path(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    result = service.readiness()

    assert result.status == "failed"
    assert result.error_code == "missing_auto_bean_on_path"
    remediation = result.details["remediation"]
    verification_command = result.details["verification_command"]
    assert isinstance(remediation, str)
    assert isinstance(verification_command, str)
    assert "uv tool install --from . --force auto-bean" in remediation
    assert verification_command == "uv tool run --from . auto-bean readiness"


def test_readiness_reports_when_auto_bean_is_not_runnable(tmp_path: Path) -> None:
    auto_bean_path = tmp_path / "bin" / "auto-bean"
    auto_bean_path.parent.mkdir()
    auto_bean_path.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    service = make_service(
        tmp_path,
        tools={
            "uv": "/opt/homebrew/bin/uv",
            "auto-bean": str(auto_bean_path),
        },
        responses={
            (str(auto_bean_path), "--help"): CommandResult(returncode=1, stderr="boom"),
        },
    )

    result = service.readiness()

    assert result.status == "failed"
    assert result.error_code == "auto_bean_unavailable"


def test_readiness_checks_installed_tool_without_repo_root_dependency(tmp_path: Path) -> None:
    auto_bean_path = tmp_path / "bin" / "auto-bean"
    auto_bean_path.parent.mkdir()
    auto_bean_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    calls: list[tuple[str, ...]] = []
    service = make_service(
        tmp_path,
        tools={
            "uv": "/opt/homebrew/bin/uv",
            "auto-bean": str(auto_bean_path),
        },
        responses={
            (str(auto_bean_path), "--help"): CommandResult(returncode=0, stdout="help"),
        },
        calls=calls,
    )

    result = service.readiness()

    assert result.status == "ok"
    assert calls == [(str(auto_bean_path), "--help")]


def test_init_is_reserved_for_later_workspace_story(tmp_path: Path) -> None:
    project_name = f"demo-ledger-{tmp_path.name[-6:]}"
    template_root = tmp_path / "workspace_template"
    (template_root / "beancount").mkdir(parents=True)
    (template_root / "docs").mkdir(parents=True)
    (template_root / ".agents" / "skills").mkdir(parents=True)
    (template_root / "statements" / "raw").mkdir(parents=True)
    (template_root / ".auto-bean").mkdir(parents=True)
    (template_root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    (template_root / "ledger.beancount").write_text(
        'option "title" "Test Ledger"\ninclude "beancount/opening-balances.beancount"\n',
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
    service = make_service(tmp_path)

    result = service.init(project_name)

    assert result.status == "ok"
    assert result.error_code is None
    assert result.details["project_name"] == project_name


def test_cli_renders_json_failure_output(
    capsys: CaptureFixture[str],
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    service = make_service(tmp_path, system="Linux")
    monkeypatch.setattr("auto_bean.cli.main.build_setup_service", lambda: service)

    exit_code = main(["readiness", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 1
    assert payload["status"] == "failed"
    assert payload["error_code"] == "unsupported_environment"
