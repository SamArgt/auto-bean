from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

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

    from auto_bean import main

    assert callable(main)


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

    def run(self, args: list[str], cwd: Path) -> CommandResult:
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
    include_dependencies: bool = True,
    create_venv: bool = True,
) -> SetupService:
    repo_root = tmp_path
    (repo_root / "src").mkdir()
    if create_venv:
        bin_dir = repo_root / ".venv" / "bin"
        bin_dir.mkdir(parents=True)
        for executable in ("python", "auto-bean", "fava", "bean-check"):
            path = bin_dir / executable
            path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")

    dependencies = ['"beancount"', '"fava"'] if include_dependencies else []
    (repo_root / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "auto-bean"',
                'version = "0.1.0"',
                "dependencies = [" + ", ".join(dependencies) + "]",
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
        tool_probe=FakeToolProbe(tools if tools is not None else {"uv": "/opt/homebrew/bin/uv"}),
        command_runner=FakeCommandRunner(responses if responses is not None else {}, calls=calls),
    )


def test_bootstrap_fails_on_unsupported_os(tmp_path: Path) -> None:
    service = make_service(tmp_path, system="Linux")

    result = service.bootstrap()

    assert result.status == "failed"
    assert result.error_code == "unsupported_environment"
    assert result.checks[0].details["detected_system"] == "Linux"


def test_bootstrap_reports_missing_uv_prerequisite(tmp_path: Path) -> None:
    service = make_service(tmp_path, tools={})

    result = service.bootstrap()

    assert result.status == "failed"
    assert result.error_code == "missing_uv"
    assert "Install uv" in result.checks[1].details["remediation"]


def test_bootstrap_accepts_version_pinned_dependencies(tmp_path: Path) -> None:
    python_path = tmp_path / ".venv" / "bin" / "python"
    service = make_service(
        tmp_path,
        responses={
            ("uv", "sync"): CommandResult(returncode=0, stdout="synced"),
            (str(python_path), "-c", "import auto_bean, beancount, fava"): CommandResult(returncode=0),
        },
    )
    (tmp_path / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "auto-bean"',
                'version = "0.1.0"',
                'dependencies = ["beancount>=3.2.0", "fava[foo]>=1.30.0; sys_platform == \'darwin\'"]',
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = service.bootstrap()

    assert result.status == "ok"
    assert result.error_code is None


def test_bootstrap_reports_bison_only_when_sync_needs_it(tmp_path: Path) -> None:
    python_path = tmp_path / ".venv" / "bin" / "python"
    service = make_service(
        tmp_path,
        responses={
            ("uv", "sync"): CommandResult(
                returncode=1,
                stderr="Program bison win_bison found: NO found 2.3 but need: '>=3.8.0'",
            ),
            (str(python_path), "-c", "import auto_bean, beancount, fava"): CommandResult(returncode=0),
        },
    )

    result = service.bootstrap()

    assert result.status == "failed"
    assert result.error_code == "uv_sync_missing_bison"
    assert "Bison >= 3.8" in result.checks[3].details["remediation"]


def test_bootstrap_stops_before_sync_when_dependencies_are_missing(tmp_path: Path) -> None:
    calls: list[tuple[str, ...]] = []
    service = make_service(tmp_path, include_dependencies=False, calls=calls)

    result = service.bootstrap()

    assert result.status == "failed"
    assert result.error_code == "missing_declared_dependencies"
    assert calls == []


def test_bootstrap_succeeds_on_prepared_repo(tmp_path: Path) -> None:
    python_path = tmp_path / ".venv" / "bin" / "python"
    service = make_service(
        tmp_path,
        responses={
            ("uv", "sync"): CommandResult(returncode=0, stdout="synced"),
            (str(python_path), "-c", "import auto_bean, beancount, fava"): CommandResult(returncode=0),
        },
    )

    result = service.bootstrap()

    assert result.status == "ok"
    assert result.error_code is None
    assert any(check.name == "uv_sync" and check.status.value == "pass" for check in result.checks)


def test_bootstrap_reports_invalid_pyproject(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[project]\ndependencies = [\n", encoding="utf-8")

    result = service.bootstrap()

    assert result.status == "failed"
    assert result.error_code == "invalid_pyproject"


def test_readiness_fails_when_uv_environment_missing(tmp_path: Path) -> None:
    service = make_service(tmp_path, create_venv=False)

    result = service.readiness()

    assert result.status == "failed"
    assert result.error_code == "missing_uv_environment"


def test_readiness_succeeds_with_required_tooling(tmp_path: Path) -> None:
    python_path = tmp_path / ".venv" / "bin" / "python"
    entrypoint_path = tmp_path / ".venv" / "bin" / "auto-bean"
    fava_path = tmp_path / ".venv" / "bin" / "fava"
    bean_check_path = tmp_path / ".venv" / "bin" / "bean-check"
    service = make_service(
        tmp_path,
        responses={
            (str(python_path), "-c", "import auto_bean, beancount, fava"): CommandResult(returncode=0),
            (str(entrypoint_path), "--help"): CommandResult(returncode=0, stdout="help"),
            (str(fava_path), "--version"): CommandResult(returncode=0, stdout="fava 1.0"),
            (str(bean_check_path), "--help"): CommandResult(returncode=0, stdout="usage"),
        },
    )

    result = service.readiness()

    assert result.status == "ok"
    assert result.error_code is None
    assert result.duration_seconds < 120


def test_cli_renders_json_failure_output(capsys, monkeypatch, tmp_path: Path) -> None:
    service = make_service(tmp_path, system="Linux")
    monkeypatch.setattr("auto_bean.cli.main.build_setup_service", lambda: service)

    exit_code = main(["readiness", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 1
    assert payload["status"] == "failed"
    assert payload["error_code"] == "unsupported_environment"
