from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

from pytest import CaptureFixture

from auto_bean.application.smoke import run_smoke_checks
from auto_bean.domain.setup import CommandResult, EnvironmentInfo


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
        return None


class _CommandRunner:
    def run(self, args: Sequence[str], cwd: Path | None = None) -> CommandResult:
        return CommandResult(returncode=0, stdout="help")


def test_run_smoke_checks_covers_success_and_blocked_paths(
    capsys: CaptureFixture[str],
) -> None:
    exit_code = run_smoke_checks()

    payload = cast(dict[str, Any], json.loads(capsys.readouterr().out))
    results = cast(list[dict[str, Any]], payload["results"])
    assert exit_code == 0
    assert payload["status"] == "ok"
    assert [result["name"] for result in results] == [
        "init-success",
        "init-blocked",
    ]
    assert results[0]["error_code"] is None
    assert results[1]["error_code"] == "unsafe_project_name"
