from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from auto_bean import migrate, reconciliation
from auto_bean.common import WorkflowError, atomic_write
from auto_bean.review import ReviewFiles
from auto_bean.review_export import render_review_html
from auto_bean.server import dispatch
from auto_bean.validation import load_state, validate_state, status_members
from test_review import review_store, PARSED, SOURCE, complete

__all__ = ["review_store"]


def historical(
    store: ReviewFiles, state: str = "done", marked: bool = False
) -> dict[str, Any]:
    status = load_state(store.root / "statements/import-status.yml")
    entry = status["groups"]["review"]
    entry["current_status"] = state
    if marked:
        entry["legacy"] = True
    (store.root / "statements/import-status.yml").write_text(yaml.safe_dump(status))
    doc = {
        "parse_run_id": "old-run",
        "source_file": SOURCE,
        "source_fingerprint": entry["sources"][SOURCE]["source_fingerprint"],
        "source_format": "csv",
        "parsed_at": "2026-01-01T00:00:00Z",
        "parser": {"name": "old-parser"},
        "extracted_records": [],
    }
    (store.root / PARSED).write_text(json.dumps(doc))
    return status


def test_schema_forbids_unfinished_markers(review_store: ReviewFiles) -> None:
    status = historical(review_store, "final_review", True)
    with pytest.raises(WorkflowError):
        validate_state("status", review_store.root, status)


def test_panel_skips_without_reading_evidence(
    review_store: ReviewFiles, monkeypatch: pytest.MonkeyPatch
) -> None:
    status = historical(review_store, marked=True)
    assert SOURCE in status_members(status)

    def forbidden(source: str) -> dict[str, Any]:
        pytest.fail("Legacy detail must not be requested")

    monkeypatch.setattr(
        ReviewFiles, "statement", lambda self, source: forbidden(source)
    )
    overview = dispatch(
        "read_import_session",
        {"workspace": str(review_store.root), "session_id": review_store.session_id},
    )
    assert overview["groups"] == overview["statements"] == []
    assert overview["review_batch"]["blockers"] == []
    html = render_review_html(review_store.root, review_store.session_id)
    assert SOURCE not in html


def test_direct_reads_and_mutations_rejected(review_store: ReviewFiles) -> None:
    historical(review_store, marked=True)
    before = (review_store.root / PARSED).read_bytes()
    with pytest.raises(WorkflowError, match="excluded from review"):
        review_store.statement(SOURCE)
    with pytest.raises(WorkflowError, match="excluded from review"):
        review_store.submit(
            SOURCE,
            {"kind": "approve", "subject_id": "statement", "expected_etag": "stale"},
        )
    assert (review_store.root / PARSED).read_bytes() == before


def test_validation_excludes_history_but_checks_ledger(
    review_store: ReviewFiles,
) -> None:
    historical(review_store, marked=True)
    before = (review_store.root / PARSED).read_bytes()
    result = reconciliation.validate_import(review_store.root, review_store.session_id)
    assert result["state"] == "passed", result
    assert result["historical_exclusions"] == ["review"]
    assert result["statements"] == {}
    assert result["groups"]["review"]["state"] == "skipped"
    assert (review_store.root / PARSED).read_bytes() == before
    (review_store.root / "ledger.beancount").write_text("invalid ledger syntax")
    assert (
        reconciliation.validate_import(review_store.root, review_store.session_id)[
            "state"
        ]
        == "failed"
    )


def test_marker_migration_preserves_evidence_and_is_idempotent(
    review_store: ReviewFiles, monkeypatch: pytest.MonkeyPatch
) -> None:
    historical(review_store)
    monkeypatch.setattr(migrate, "ensure_runtime", lambda root: root)
    monkeypatch.setattr(migrate, "validate", lambda root, env: None)
    before = (review_store.root / PARSED).read_bytes()
    plan = migrate.plan_migration(review_store.root)
    assert [c["path"] for c in plan["changes"]] == ["statements/import-status.yml"]
    result = migrate.apply_migration(review_store.root, plan["plan_id"])
    assert Path(str(result["backup"]), "statements/import-status.yml").is_file()
    assert (
        load_state(review_store.root / "statements/import-status.yml")["groups"][
            "review"
        ]["legacy"]
        is True
    )
    assert (review_store.root / PARSED).read_bytes() == before
    assert migrate.plan_migration(review_store.root)["changes"] == []
    assert migrate.apply_migration(review_store.root, plan["plan_id"])["status"] == "ok"


@pytest.mark.parametrize("damage", ["unfinished", "missing", "malformed", "unknown"])
def test_preflight_blocks_bad_evidence(review_store: ReviewFiles, damage: str) -> None:
    historical(review_store, "final_review" if damage == "unfinished" else "done")
    path = review_store.root / PARSED
    if damage == "missing":
        path.unlink()
    elif damage == "malformed":
        path.write_text("{")
    elif damage == "unknown":
        path.write_text('{"anything": true}')
    with pytest.raises((WorkflowError, OSError)):
        migrate.plan_migration(review_store.root)
    assert not (review_store.root / ".auto-bean/migrations").exists()


def test_evidence_changes_invalidate_plan(review_store: ReviewFiles) -> None:
    historical(review_store)
    plan = migrate.plan_migration(review_store.root)
    path = review_store.root / PARSED
    path.write_text(path.read_text() + "\n")
    with pytest.raises(WorkflowError, match="fresh migration plan"):
        migrate.apply_migration(review_store.root, plan["plan_id"])


def test_resume_checks_evidence_before_mutation(
    review_store: ReviewFiles, monkeypatch: pytest.MonkeyPatch
) -> None:
    historical(review_store)
    monkeypatch.setattr(migrate, "ensure_runtime", lambda root: root)
    monkeypatch.setattr(migrate, "validate", lambda root, env: None)
    plan = migrate.plan_migration(review_store.root)

    def interrupt(path: Path, data: bytes) -> None:
        atomic_write(path, data)
        if path.name == "journal.json":
            raise OSError("interrupted")

    monkeypatch.setattr(migrate, "atomic_write", interrupt)
    with pytest.raises(OSError, match="interrupted"):
        migrate.apply_migration(review_store.root, plan["plan_id"])
    monkeypatch.setattr(migrate, "atomic_write", atomic_write)
    historical(review_store, "final_review")
    with pytest.raises(WorkflowError, match="compatible workflow"):
        migrate.apply_migration(review_store.root, plan["plan_id"])
    assert not load_state(review_store.root / "statements/import-status.yml")["groups"][
        "review"
    ].get("legacy")


def test_mixed_session_keeps_modern_validation(review_store: ReviewFiles) -> None:
    complete(review_store)
    root = review_store.root
    status = load_state(root / "statements/import-status.yml")
    status["groups"]["review"]["current_status"] = "final_review"
    old_source = "statements/raw/old.csv"
    old_path = "statements/parsed/old.json"
    status["groups"]["old"] = {
        **status["groups"]["review"],
        "current_status": "done",
        "legacy": True,
        "parsed_group": old_path,
        "sources": {old_source: status["groups"]["review"]["sources"][SOURCE]},
    }
    (root / "statements/import-status.yml").write_text(yaml.safe_dump(status))
    (root / old_source).write_bytes((root / SOURCE).read_bytes())
    (root / old_path).write_text('{"historical": "do not load as modern evidence"}')
    session = load_state(root / review_store.session_path)
    session["groups"].append(
        {
            **session["groups"][0],
            "group_id": "old",
            "parsed_group": old_path,
            "source_files": [old_source],
        }
    )
    (root / review_store.session_path).write_text(json.dumps(session))
    overview = dispatch(
        "read_import_session",
        {"workspace": str(root), "session_id": review_store.session_id},
    )
    assert [g["group_id"] for g in overview["groups"]] == ["review"]
    report = reconciliation.validate_import(root, review_store.session_id, "review")
    assert report["state"] == "passed", report
    assert report["historical_exclusions"] == ["old"]
    assert report["statements"][SOURCE]["state"] == "passed"
