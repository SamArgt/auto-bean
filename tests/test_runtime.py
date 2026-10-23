from __future__ import annotations

import shutil
import os
import platform
from collections.abc import Callable
from pathlib import Path

import pytest

from auto_bean import common, runtime
from auto_bean.common import WorkflowError, atomic_write, json_bytes, workspace


@pytest.fixture
def plugin(tmp_path: Path) -> Path:
    root = tmp_path / "plugin"
    (root / "runtime").mkdir(parents=True)
    (root / "runtime/pyproject.toml").write_text("first manifest")
    (root / "runtime/uv.lock").write_text("first lock")
    return root


@pytest.fixture
def prepared(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    built: list[Path] = []
    monkeypatch.setattr(runtime, "prerequisites", lambda: None)

    def sync(args: list[str], *, cwd: Path, env: dict[str, str]) -> str:
        destination = Path(env["UV_PROJECT_ENVIRONMENT"])
        destination.mkdir(parents=True)
        (destination / "healthy").touch()
        built.append(destination)
        return ""

    monkeypatch.setattr(runtime, "run_checked", sync)
    monkeypatch.setattr(
        runtime,
        "healthy",
        lambda environment, **kwargs: (environment / "healthy").is_file(),
    )
    return built


def test_reuses_healthy_runtime_and_never_writes_to_plugin(
    current: Path, plugin: Path, prepared: list[Path]
) -> None:
    before = {p: p.read_bytes() for p in plugin.rglob("*") if p.is_file()}
    first = runtime.ensure_runtime(current, plugin=plugin)
    assert runtime.ensure_runtime(current, plugin=plugin) == first
    assert prepared == [first]
    assert before == {p: p.read_bytes() for p in plugin.rglob("*") if p.is_file()}


def test_two_releases_and_two_ledgers_need_no_copied_product_files(
    current: Path, plugin: Path, prepared: list[Path], tmp_path: Path
) -> None:
    other = tmp_path / "other ledger"
    shutil.copytree(current, other)
    first = runtime.ensure_runtime(current, plugin=plugin)
    second = runtime.ensure_runtime(other, plugin=plugin)
    (plugin / "runtime/uv.lock").write_text("next release lock")
    updated = runtime.ensure_runtime(current, plugin=plugin)
    other_updated = runtime.ensure_runtime(other, plugin=plugin)
    assert first != updated and second != other_updated
    assert all(path.exists() for path in (first, second, updated, other_updated))
    assert len(prepared) == 4


def test_failed_new_generation_keeps_healthy_previous_runtime(
    current: Path, plugin: Path, prepared: list[Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    first = runtime.ensure_runtime(current, plugin=plugin)
    old_key = runtime.fingerprint(plugin)
    (plugin / "runtime/uv.lock").write_text("new lock")

    def fail(args: list[str], *, cwd: Path, env: dict[str, str]) -> str:
        Path(env["UV_PROJECT_ENVIRONMENT"]).mkdir(parents=True)
        raise WorkflowError("download_failed", "offline")

    monkeypatch.setattr(runtime, "run_checked", fail)
    with pytest.raises(WorkflowError):
        runtime.ensure_runtime(current, plugin=plugin)
    assert (first / "healthy").is_file()
    assert (first.parent / "ready").read_text() == old_key
    assert not (
        current / ".auto-bean/runtime" / runtime.fingerprint(plugin) / "ready"
    ).exists()


def test_broken_runtime_is_rebuilt(
    current: Path, plugin: Path, prepared: list[Path]
) -> None:
    environment = runtime.ensure_runtime(current, plugin=plugin)
    (environment / "healthy").unlink()
    assert runtime.ensure_runtime(current, plugin=plugin) == environment
    assert len(prepared) == 2


def test_workspace_and_runtime_symlinks_are_rejected(
    current: Path, plugin: Path, tmp_path: Path
) -> None:
    target = tmp_path / "external"
    target.mkdir()
    (current / ".auto-bean/runtime").symlink_to(target, target_is_directory=True)
    with pytest.raises(WorkflowError, match="symlink"):
        runtime.ensure_runtime(current, plugin=plugin)


def test_legacy_and_unknown_formats_stop_before_tool_execution(legacy: Path) -> None:
    with pytest.raises(WorkflowError, match="auto-bean-migrate"):
        workspace(legacy)
    atomic_write(legacy / common.STATE, json_bytes({"format_version": 99}))
    with pytest.raises(WorkflowError, match="compatible"):
        workspace(legacy)


def test_incomplete_migration_blocks_operations_even_after_format_marker(
    current: Path,
) -> None:
    atomic_write(
        current / ".auto-bean/migrations/reviewed/journal.json",
        json_bytes({"status": "applying"}),
    )
    with pytest.raises(WorkflowError, match="unfinished migration"):
        workspace(current)


@pytest.mark.parametrize("system", ["Darwin", "Linux"])
def test_supported_platforms(system: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(platform, "system", lambda: system)
    monkeypatch.setattr(shutil, "which", lambda tool: "/bin/" + tool)
    common.prerequisites(git=True)


def test_missing_tools_and_unsupported_platform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    with pytest.raises(WorkflowError, match="macOS and Linux"):
        common.prerequisites()
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(shutil, "which", lambda tool: None)
    with pytest.raises(WorkflowError, match="Install uv"):
        common.prerequisites()


def test_base_and_extraction_generations_are_isolated(
    current: Path, plugin: Path, prepared: list[Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    sync: Callable[..., str] = getattr(runtime, "run_checked")
    commands: list[list[str]] = []

    def record(args: list[str], *, cwd: Path, env: dict[str, str]) -> str:
        commands.append(args)
        return sync(args, cwd=cwd, env=env)

    monkeypatch.setattr(runtime, "run_checked", record)
    base = runtime.ensure_runtime(current, plugin=plugin)
    extraction = runtime.ensure_runtime(current, plugin=plugin, extraction=True)
    assert base != extraction
    assert "--extra" not in commands[0]
    assert commands[1][-2:] == ["--extra", "extraction"]
    assert runtime.ensure_runtime(current, plugin=plugin) == base
    assert prepared == [base, extraction]


def test_failed_extraction_preserves_usable_base(
    current: Path, plugin: Path, prepared: list[Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    base = runtime.ensure_runtime(current, plugin=plugin)

    def fail(args: list[str], *, cwd: Path, env: dict[str, str]) -> str:
        raise WorkflowError("download_failed", "Extraction offline")

    monkeypatch.setattr(runtime, "run_checked", fail)
    with pytest.raises(WorkflowError, match="offline"):
        runtime.ensure_runtime(current, plugin=plugin, extraction=True)
    assert runtime.ensure_runtime(current, plugin=plugin) == base


@pytest.mark.parametrize(
    "session,price_run",
    [(None, None), ("import-session", None), ("import-session", "prices")],
)
def test_validation_uses_managed_runtime(
    current: Path,
    monkeypatch: pytest.MonkeyPatch,
    session: str | None,
    price_run: str | None,
) -> None:
    from auto_bean import __main__ as launcher

    calls: list[tuple[Path, str, list[str]]] = []

    def run(root: Path, tool: str, args: list[str]) -> int:
        calls.append((root, tool, args))
        return 1

    monkeypatch.setattr(launcher, "run_tool", run)
    args = ["validate", "--workspace", str(current), "--stage", "review"]
    if session:
        args.extend(["--session", session])
    if price_run:
        args.extend(["--price-run", price_run])
    assert launcher.main(args) == 1  # A failed validation remains a failed command.
    assert calls == [
        (
            current,
            "python",
            [
                "-m",
                "auto_bean.reconciliation",
                "--workspace",
                str(current),
                "--stage",
                "review",
                *(["--session", session] if session else []),
                *(["--price-run", price_run] if price_run else []),
            ],
        )
    ]


@pytest.mark.parametrize("tool", ["docling", "docling-tools", "python", "bean-query"])
def test_runtime_routes_model_preparation_and_extraction_to_same_environment(
    current: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tool: str
) -> None:
    from typing import NoReturn

    environment = tmp_path / "managed/.venv"
    selected: list[bool] = []

    def ensure(root: Path, *, extraction: bool = False) -> Path:
        assert root == current
        selected.append(extraction)
        return environment

    def execute(path: Path, args: list[str], env: dict[str, str]) -> NoReturn:
        assert path == environment / "bin" / tool
        assert args == [tool, "--help"]
        assert env["VIRTUAL_ENV"] == str(environment)
        assert env["PATH"].split(":")[0] == str(environment / "bin")
        raise SystemExit(0)

    monkeypatch.setattr(runtime, "ensure_runtime", ensure)
    monkeypatch.setattr(os, "chdir", lambda root: None)
    monkeypatch.setattr(os, "execve", execute)
    with pytest.raises(SystemExit) as result:
        runtime.run_tool(current, tool, ["--help"])
    assert result.value.code == 0
    assert selected == [tool in {"docling", "docling-tools"}]
