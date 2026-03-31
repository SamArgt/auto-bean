from __future__ import annotations

import json
from collections.abc import Sequence
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
        return self.responses.get(tuple(args), CommandResult(returncode=0))


def make_service(
    tmp_path: Path,
    *,
    system: str = "Darwin",
    tools: dict[str, str] | None = None,
    responses: dict[tuple[str, ...], CommandResult] | None = None,
    calls: list[tuple[str, ...]] | None = None,
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
            tools if tools is not None else {"uv": "/opt/homebrew/bin/uv"}
        ),
        command_runner=FakeCommandRunner(responses if responses is not None else {}, calls=calls),
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
    assert "uv tool install --from . --force auto-bean" in result.checks[1].details["remediation"]


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
    assert "uv tool install --from . --force auto-bean" in result.details["remediation"]
    assert result.details["verification_command"] == "uv tool run --from . auto-bean readiness"


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
    service = make_service(tmp_path)

    result = service.init("demo-ledger")

    assert result.status == "failed"
    assert result.error_code == "init_not_implemented"
    assert result.details["project_name"] == "demo-ledger"


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
