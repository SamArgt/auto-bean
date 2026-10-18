from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from auto_bean import migrate
from auto_bean.common import STATE, WorkflowError, atomic_write, json_bytes, read_json


@pytest.fixture(autouse=True)
def runtime(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        migrate, "ensure_runtime", lambda root: tmp_path / "environment"
    )
    monkeypatch.setattr(migrate, "validate", lambda root, environment: None)


def snapshot(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file()
    }


def test_inventory_is_read_only_and_reports_customizations(legacy: Path) -> None:
    before = snapshot(legacy)
    plan = migrate.plan_migration(legacy)
    assert plan["status"] == "review_required"
    changes = {change["path"]: change for change in plan["changes"]}
    assert changes["AGENTS.md"]["classification"] == "customized_or_unknown"
    assert changes[".agents/skills/auto-bean-query/SKILL.md"]["operation"] == "remove"
    assert "personal" not in " ".join(changes)
    assert snapshot(legacy) == before


def test_apply_preserves_data_customizations_and_git_history(legacy: Path) -> None:
    subprocess.run(["git", "init"], cwd=legacy, check=True, capture_output=True)
    subprocess.run(["git", "add", "--all"], cwd=legacy, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Existing ledger"],
        cwd=legacy,
        check=True,
        capture_output=True,
    )
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=legacy)
    before = snapshot(legacy)
    plan = migrate.plan_migration(legacy)
    result = migrate.apply_migration(legacy, plan["plan_id"])
    assert result["status"] == "ok"
    backup = Path(str(result["backup"]))
    changed = {change["path"] for change in plan["changes"]}
    for relative, data in before.items():
        if relative in changed:
            assert (backup / relative).read_bytes() == data
        elif not relative.startswith(".git/"):
            assert (legacy / relative).read_bytes() == data, relative
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=legacy) == head
    assert not (legacy / ".agents/skills/auto-bean-query/SKILL.md").exists()
    assert (legacy / ".agents/skills/personal/SKILL.md").is_file()
    assert (legacy / "scripts/personal.sh").is_file()
    assert read_json(legacy / STATE) == {"format_version": 1}
    assert migrate.plan_migration(legacy)["changes"] == []
    assert migrate.apply_migration(legacy, plan["plan_id"])["status"] == "ok"
    ignored = subprocess.check_output(
        ["git", "check-ignore", str(backup / "AGENTS.md")], cwd=legacy, text=True
    )
    assert "migrations" in ignored


def test_changed_plan_cannot_be_applied(legacy: Path) -> None:
    plan = migrate.plan_migration(legacy)
    (legacy / "README.md").write_text("new user edit")
    with pytest.raises(WorkflowError, match="fresh migration plan"):
        migrate.apply_migration(legacy, plan["plan_id"])
    assert (legacy / ".agents/skills/auto-bean-query/SKILL.md").exists()


def test_interruption_resumes_without_replacing_original_backups(
    legacy: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = migrate.plan_migration(legacy)
    original = (legacy / "AGENTS.md").read_bytes()
    write = atomic_write
    calls = 0

    def interrupt(path: Path, data: bytes) -> None:
        nonlocal calls
        write(path, data)
        calls += 1
        if calls == 3:
            raise OSError("simulated interruption")

    monkeypatch.setattr(migrate, "atomic_write", interrupt)
    with pytest.raises(OSError, match="interruption"):
        migrate.apply_migration(legacy, plan["plan_id"])
    monkeypatch.setattr(migrate, "atomic_write", write)
    result = migrate.apply_migration(legacy, plan["plan_id"])
    assert (Path(str(result["backup"])) / "AGENTS.md").read_bytes() == original


def test_concurrent_changes_block_resume(
    legacy: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = migrate.plan_migration(legacy)
    write = atomic_write

    def interrupt(path: Path, data: bytes) -> None:
        write(path, data)
        if path.name == "AGENTS.md":
            raise OSError("simulated interruption")

    monkeypatch.setattr(migrate, "atomic_write", interrupt)
    with pytest.raises(OSError):
        migrate.apply_migration(legacy, plan["plan_id"])
    monkeypatch.setattr(migrate, "atomic_write", write)
    (legacy / "AGENTS.md").write_text("concurrent edit")
    with pytest.raises(WorkflowError, match="Changed during migration"):
        migrate.apply_migration(legacy, plan["plan_id"])
    assert (legacy / "AGENTS.md").read_text() == "concurrent edit"


def test_symlink_retirement_is_rejected(legacy: Path, tmp_path: Path) -> None:
    target = legacy / "scripts/validate-ledger.sh"
    target.unlink()
    outside = tmp_path / "private"
    outside.write_text("keep")
    target.symlink_to(outside)
    with pytest.raises(WorkflowError, match="symlink"):
        migrate.plan_migration(legacy)
    assert outside.read_text() == "keep"


def test_invalid_ledger_blocks_retirement(
    legacy: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = migrate.plan_migration(legacy)
    before = snapshot(legacy)

    def fail(root: Path, environment: Path) -> None:
        raise WorkflowError("invalid_ledger", "Invalid ledger")

    monkeypatch.setattr(migrate, "validate", fail)
    with pytest.raises(WorkflowError):
        migrate.apply_migration(legacy, plan["plan_id"])
    assert snapshot(legacy) == before


def test_journal_contents_cannot_change_after_review(legacy: Path) -> None:
    plan = migrate.plan_migration(legacy)
    migrate.apply_migration(legacy, plan["plan_id"])
    journal_path = legacy / f".auto-bean/migrations/{plan['plan_id']}/journal.json"
    journal = read_json(journal_path)
    journal["changes"][0]["content"] = "tampered"
    atomic_write(journal_path, json_bytes(journal))
    with pytest.raises(WorkflowError, match="contents changed"):
        migrate.apply_migration(legacy, plan["plan_id"])
