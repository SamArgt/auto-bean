from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from auto_bean.init import (
    CommandResult,
    EnvironmentInfo,
    InitService,
    ProjectPaths,
)


class FakePlatform:
    def inspect(self) -> EnvironmentInfo:
        return EnvironmentInfo(
            system="Darwin",
            release="24.0",
            machine="arm64",
            python_version="3.13.0",
        )


class FakeTools:
    def find(self, command: str) -> str | None:
        known = {"uv", "git"}
        return f"/usr/bin/{command}" if command in known else None


class FakeCommands:
    def run(self, args: Sequence[str], cwd: Path | None = None) -> CommandResult:
        del cwd
        if len(args) >= 2 and args[0].endswith("fava") and args[1] == "--version":
            return CommandResult(returncode=0, stdout="fava 0.0")
        if len(args) >= 2 and args[0].endswith("docling") and args[1] == "--version":
            return CommandResult(returncode=0, stdout="docling 0.0")
        return CommandResult(returncode=0, stdout="")


def test_init_copies_reconciliation_reference_into_workspace(tmp_path: Path) -> None:
    service = InitService(
        paths=ProjectPaths(start=tmp_path),
        platform=FakePlatform(),
        tools=FakeTools(),
        commands=FakeCommands(),
        prompt=lambda _: "Codex",
    )

    result = service.init("ledger-demo")

    assert result.status == "ok"
    workspace = tmp_path / "ledger-demo"
    reference_path = (
        workspace
        / ".agents"
        / "skills"
        / "auto-bean-apply"
        / "references"
        / "reconciliation-findings.md"
    )
    assert reference_path.is_file()
    created_paths = result.details["created_paths"]
    assert isinstance(created_paths, list)
    assert (
        ".agents/skills/auto-bean-apply/references/reconciliation-findings.md"
    ) in created_paths


def test_init_copies_clarification_guidance_into_workspace(tmp_path: Path) -> None:
    service = InitService(
        paths=ProjectPaths(start=tmp_path),
        platform=FakePlatform(),
        tools=FakeTools(),
        commands=FakeCommands(),
        prompt=lambda _: "Codex",
    )

    result = service.init("ledger-demo")

    assert result.status == "ok"
    workspace = tmp_path / "ledger-demo"
    guidance_path = (
        workspace
        / ".agents"
        / "skills"
        / "auto-bean-apply"
        / "references"
        / "clarification-guidance.md"
    )
    assert guidance_path.is_file()
    created_paths = result.details["created_paths"]
    assert isinstance(created_paths, list)
    assert (
        ".agents/skills/auto-bean-apply/references/clarification-guidance.md"
    ) in created_paths
