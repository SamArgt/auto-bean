"""Tool receipts must describe actual governed file writes."""

from pathlib import Path

import pytest

from auto_bean.common import atomic_write, change_report, digest, record_changes


def test_receipt_tracks_final_bytes_and_excludes_unchanged_files(
    tmp_path: Path,
) -> None:
    existing = tmp_path / "existing.json"
    existing.write_bytes(b"original")
    with record_changes() as changes:
        atomic_write(existing, b"changed")
        atomic_write(existing, b"original")
        atomic_write(tmp_path / "created.json", b"first")
        atomic_write(tmp_path / "created.json", b"final")
        atomic_write(tmp_path / "same.json", b"same")
    assert change_report(tmp_path, changes) == {
        "changed_files": ["created.json", "same.json"],
        "file_sha256": {"created.json": digest(b"final"), "same.json": digest(b"same")},
    }
    with record_changes() as unchanged:
        atomic_write(existing, b"original")
    assert change_report(tmp_path, unchanged) == {
        "changed_files": [],
        "file_sha256": {},
    }


def test_receipt_survives_operation_failure_and_resets_context(tmp_path: Path) -> None:
    with pytest.raises(ValueError), record_changes() as changes:
        atomic_write(tmp_path / "saved.json", b"saved")
        raise ValueError("later failure")
    atomic_write(tmp_path / "untracked.json", b"untracked")
    assert change_report(tmp_path, changes)["changed_files"] == ["saved.json"]


def test_receipt_excludes_files_outside_workspace(tmp_path: Path) -> None:
    root = tmp_path / "ledger"
    root.mkdir()
    with record_changes() as changes:
        atomic_write(tmp_path / "outside.json", b"outside")
        atomic_write(root / "inside.json", b"inside")
    assert change_report(root, changes)["changed_files"] == ["inside.json"]
