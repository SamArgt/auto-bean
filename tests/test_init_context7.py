from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from pathlib import Path
from stat import S_IMODE
from typing import Any, cast

from click.testing import CliRunner

from auto_bean import cli as cli_module
from auto_bean.init import (
    CheckStatus,
    CommandExecutor,
    CommandResult,
    EnvironmentInfo,
    InitService,
    PlatformInspector,
    ProjectPaths,
    ToolLocator,
)


class FakePlatform(PlatformInspector):
    def inspect(self) -> EnvironmentInfo:
        return EnvironmentInfo(
            system="Darwin",
            release="test",
            machine="arm64",
            python_version="3.13.0",
        )


class FakeTools(ToolLocator):
    def find(self, command: str) -> str | None:
        return f"/usr/bin/{command}"


class RecordingCommands(CommandExecutor):
    def __init__(self) -> None:
        self.calls: list[tuple[tuple[str, ...], Path | None]] = []

    def run(self, args: Sequence[str], cwd: Path | None = None) -> CommandResult:
        self.calls.append((tuple(args), cwd))
        return CommandResult(returncode=0)


def build_service(
    tmp_path: Path, *, secret_prompt: Callable[[str], str] | None = None
) -> InitService:
    return InitService(
        paths=ProjectPaths(start=tmp_path),
        platform=FakePlatform(),
        tools=FakeTools(),
        commands=RecordingCommands(),
        prompt=lambda _message: "Codex",
        secret_prompt=secret_prompt or (lambda _message: ""),
    )


def test_init_writes_gitignored_context7_config_with_secret(tmp_path: Path) -> None:
    service = build_service(tmp_path)

    result = service.init(
        "ledger",
        coding_agent="Codex",
        context7_api_key=" context7-secret ",
    )

    target = tmp_path / "ledger"
    assert result.status == "ok"
    assert result.details["context7_mcp"] == "configured"
    assert result.details["context7_api_key_status"] == "stored"
    assert (target / ".codex" / "config.toml").read_text(encoding="utf-8") == (
        "[mcp_servers.context7]\n"
        'url = "https://mcp.context7.com/mcp"\n'
        'http_headers = { "CONTEXT7_API_KEY" = "context7-secret" }\n'
    )
    assert S_IMODE((target / ".codex" / "config.toml").stat().st_mode) == 0o600
    assert ".codex/config.toml\n" in (target / ".gitignore").read_text(encoding="utf-8")
    created_paths = cast(list[str], result.details["created_paths"])
    assert ".codex/config.toml" in created_paths


def test_init_uses_environment_backed_context7_config_when_key_is_blank(
    tmp_path: Path,
) -> None:
    service = build_service(tmp_path)

    result = service.init("ledger", coding_agent="Codex", context7_api_key=" ")

    target = tmp_path / "ledger"
    assert result.status == "ok"
    assert result.details["context7_api_key_status"] == "not_provided"
    assert (target / ".codex" / "config.toml").read_text(encoding="utf-8") == (
        "[mcp_servers.context7]\n"
        'url = "https://mcp.context7.com/mcp"\n'
        'env_http_headers = { "CONTEXT7_API_KEY" = "CONTEXT7_API_KEY" }\n'
    )


def test_json_init_uses_environment_context7_key_without_prompt(
    tmp_path: Path, monkeypatch: Any
) -> None:
    def fail_prompt(_message: str) -> str:
        raise AssertionError("JSON mode must not prompt for the Context7 API key")

    service = build_service(tmp_path, secret_prompt=fail_prompt)
    monkeypatch.setattr(cli_module, "build_init_service", lambda: service)

    result = CliRunner().invoke(
        cli_module.cli,
        ["init", "ledger", "--json"],
        env={"CONTEXT7_API_KEY": "json-secret"},
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["status"] == "ok"
    assert output["details"]["context7_api_key_status"] == "stored"
    assert "json-secret" in (tmp_path / "ledger" / ".codex" / "config.toml").read_text(
        encoding="utf-8"
    )


def test_cleanup_removes_partial_codex_config(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    target = tmp_path / "ledger"
    (target / ".codex").mkdir(parents=True)
    (target / ".codex" / "config.toml").write_text("partial", encoding="utf-8")

    service._cleanup_workspace(target, preserve_root=True)

    assert target.exists()
    assert not (target / ".codex").exists()


def test_workspace_template_requires_context7_config(tmp_path: Path) -> None:
    service = build_service(tmp_path)

    check = service._check_required_assets(
        name="workspace_template_available",
        details_key="template_directory",
        error_code="missing_template_assets",
        message="Workspace template assets are available.",
        failure_message="Workspace template assets are missing.",
        root=tmp_path,
        required_paths=(".codex/config.toml",),
    )

    assert check.status is CheckStatus.FAIL
    assert check.error_code == "missing_template_assets"
