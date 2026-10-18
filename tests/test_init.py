from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from auto_bean import init
from auto_bean.common import STATE, WorkflowError, read_json


@pytest.fixture(autouse=True)
def runtime(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(init, "ensure_runtime", lambda root: tmp_path / "environment")
    monkeypatch.setattr(init, "validate", lambda root, environment: None)


def test_initializes_validated_git_workspace_without_product_copies(
    tmp_path: Path,
) -> None:
    root = tmp_path / "new ledger"
    result = init.initialize(root)
    assert result["status"] == "ok"
    assert result["validated"] is True
    assert read_json(root / STATE) == {"format_version": 1}
    assert not (root / ".agents").exists()
    assert not (root / "scripts").exists()
    assert not (root / ".codex").exists()
    assert (root / "statements/raw").is_dir()
    tracked = subprocess.check_output(["git", "ls-files"], cwd=root, text=True)
    assert "ledger.beancount" in tracked
    assert ".auto-bean/memory/MEMORY.md" in tracked
    assert ".auto-bean/workspace.json" in tracked


def test_empty_current_directory_can_be_initialized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert init.initialize(Path("."))["status"] == "ok"


def test_nonempty_destination_is_never_modified(tmp_path: Path) -> None:
    sentinel = tmp_path / "keep"
    sentinel.write_text("user work")
    with pytest.raises(WorkflowError, match="empty destination"):
        init.initialize(tmp_path)
    assert list(tmp_path.iterdir()) == [sentinel]


def test_missing_identity_keeps_validated_scaffold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GIT_AUTHOR_NAME", "")
    root = tmp_path / "ledger"
    result = init.initialize(root)
    assert result["status"] == "needs_input"
    assert result["validated"] is True
    assert (root / "ledger.beancount").is_file()
    assert (root / ".git").is_dir()


def test_runtime_failure_preserves_preexisting_empty_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(root: Path) -> Path:
        raise WorkflowError("download_failed", "Network unavailable")

    monkeypatch.setattr(init, "ensure_runtime", fail)
    with pytest.raises(WorkflowError):
        init.initialize(tmp_path)
    assert tmp_path.is_dir()
    assert not list(tmp_path.iterdir())


def test_failure_does_not_discard_concurrent_user_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "ledger"

    def fail(destination: Path) -> Path:
        (destination / "user-notes.txt").write_text("keep this")
        (destination / "ledger.beancount").write_text("user edit")
        raise WorkflowError("download_failed", "Network unavailable")

    monkeypatch.setattr(init, "ensure_runtime", fail)
    with pytest.raises(WorkflowError):
        init.initialize(root)
    assert (root / "user-notes.txt").read_text() == "keep this"
    assert (root / "ledger.beancount").read_text() == "user edit"


def test_symlink_and_file_destinations_are_rejected(tmp_path: Path) -> None:
    link = tmp_path / "link"
    other = tmp_path / "other"
    other.mkdir()
    link.symlink_to(other, target_is_directory=True)
    with pytest.raises(WorkflowError):
        init.initialize(link)
    file = tmp_path / "file"
    file.touch()
    with pytest.raises(WorkflowError):
        init.initialize(file)
