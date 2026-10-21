from __future__ import annotations

import copy
import html
import json
from html.parser import HTMLParser
from pathlib import Path

import pytest
import yaml

from auto_bean.common import WorkflowError, digest
from auto_bean.review import ReviewFiles, etag, material
from auto_bean.review_export import export_review_html, render_review_html
from auto_bean.server import CONTRACTS, dispatch, output_schema, validate
from test_review import BASE, PARSED, SOURCE, complete, review_store, save

__all__ = ["review_store"]


class Tags(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []
        self.attributes: list[tuple[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)
        self.attributes.extend(attrs)


def files(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file() and "exports" not in p.parts and p.name != "review.lock"
    }


def test_export_partial_and_failed_state_without_canonical_mutation(
    review_store: ReviewFiles,
) -> None:
    store = review_store
    document = store.statement(SOURCE)
    document["extraction_state"] = "failed"
    document["review"]["processing"].update(
        attempts=1, outcome="failed", failure_reason="Unreadable scan"
    )
    save(store, PARSED, document)
    before = files(store.root)
    result = export_review_html(store.root, store.session_id)
    path = Path(result["path"])
    page = path.read_text()
    assert files(store.root) == before
    assert path.parent == store.root / ".auto-bean/exports"
    assert result["filename"] == path.name
    assert result["sha256"] == digest(path.read_bytes())
    assert "Read-only snapshot captured" in page
    assert result["exported_at"] in page
    assert "Unreadable scan" in page
    assert "Extraction: failed" in page
    assert "Account evidence is not available yet" in page
    assert "No live updates, corrections or approvals" in page
    second = export_review_html(store.root, store.session_id)
    assert second["path"] != result["path"]
    assert path.read_text() == page


def test_export_includes_all_rows_and_escapes_active_content(
    review_store: ReviewFiles,
) -> None:
    store = review_store
    doc = complete(store)
    attack = '</pre><script>alert("leak")</script><img src="https://bad.test/x" onerror="alert(1)">'
    evidence = {
        key: copy.deepcopy(doc[key])
        for key in ("statement_metadata", "extracted_records")
    }
    for account in evidence["statement_metadata"]["accounts"]:
        account.pop("review", None)
    for record in evidence["extracted_records"]:
        record.pop("review", None)
    evidence["statement_metadata"]["accounts"][0]["account_name"] = attack
    evidence["statement_metadata"]["accounts"][0]["closing_balance"] = {
        "date": "2026-01-31",
        "amount": "-25",
        "currency": "EUR",
    }
    original = evidence["extracted_records"][0]
    original["description"] = attack
    for index in range(2, 126):
        row = copy.deepcopy(original)
        row.update(
            record_id=f"row-{index}",
            source_reference=f"row:{index}",
            description=f"Export row {index}",
        )
        evidence["extracted_records"].append(row)
    doc.update(evidence)
    doc["statement_metadata"]["accounts"][0]["review"] = {
        "state": "confirmed",
        "ledger_account": "Assets:Checking",
        "rationale": attack,
        "suggestions": [attack],
        "answer": attack,
    }
    doc["extracted_records"][0]["review"] = {
        "state": "needs_input",
        "disposition": "hold",
        "postings": [],
        "rationale": "Changed evidence needs confirmation",
    }
    save(store, PARSED, doc)
    page = render_review_html(store.root, store.session_id)
    assert "Transactions (125)" in page
    assert "Export row 125" in page
    assert "-25 EUR · 2026-01-31" in page
    assert html.escape(attack, quote=True) in page
    assert attack not in page
    tags = Tags()
    tags.feed(page)
    assert not {
        "script",
        "img",
        "iframe",
        "form",
        "button",
        "input",
        "link",
    }.intersection(tags.tags)
    assert not any(k.startswith("on") or k == "src" for k, _ in tags.attributes)
    assert all((v or "").startswith("#") for k, v in tags.attributes if k == "href")
    assert "default-src 'none'" in page
    assert "Snapshot review data (JSON)" in page
    # Changed evidence on the reviewed first row requires renewed input; the
    # 124 new rows remain pending without a human-input highlight.
    assert page.count("⚠ Needs input · ") == 1
    assert "&quot;revision&quot;" not in page


def test_export_excludes_other_sessions_and_rejects_corrupt_membership(
    review_store: ReviewFiles,
) -> None:
    store = review_store
    complete(store)
    status_path = store.root / "statements/import-status.yml"
    status = yaml.safe_load(status_path.read_text())
    other_source = "statements/raw/unrelated.csv"
    other_parsed = "statements/parsed/unrelated.json"
    (store.root / other_source).write_text("Other private statement")
    status["groups"]["other"] = {
        "session_id": "another-session",
        "current_status": "raw_ready",
        "parsed_group": other_parsed,
        "sources": {
            other_source: {
                "source_fingerprint": "sha256:"
                + digest((store.root / other_source).read_bytes())
            }
        },
    }
    status_path.write_text(yaml.safe_dump(status))
    other = store.read(store.session_path)
    other["session_id"] = "another-session"
    other["groups"][0].update(
        group_id="other", source_files=[other_source], parsed_group=other_parsed
    )
    (store.root / ".auto-bean/import-sessions/another-session.json").write_text(
        json.dumps(other)
    )
    page = render_review_html(store.root, store.session_id)
    assert "unrelated.csv" not in page
    assert "another-session" not in page
    doc = store.statement(SOURCE)
    doc["source_file"] = other_source
    save(store, PARSED, doc)
    with pytest.raises(WorkflowError):
        render_review_html(store.root, store.session_id)


def test_export_keeps_reviewed_postings_without_ledger_contents(
    review_store: ReviewFiles,
) -> None:
    store = review_store
    marker = "Unrelated historical transaction beyond review data"
    (store.root / "ledger.beancount").write_text(BASE + f"; {marker}\n")
    complete(store)
    before = files(store.root)
    page = render_review_html(store.root, store.session_id)
    assert files(store.root) == before
    assert marker not in page
    assert "Expenses:Food" in page
    assert "No panel confirmation" in page
    assert (
        "Raw statement attachments and full ledger-file contents are excluded" in page
    )
    assert "changes" not in store.read(store.session_path)
    assert "actions" not in store.read(store.session_path)


def test_export_shows_statement_approval_without_claiming_validation(
    review_store: ReviewFiles,
) -> None:
    store = review_store
    document = complete(store)
    status_path = store.root / "statements/import-status.yml"
    status = yaml.safe_load(status_path.read_text())
    status["groups"]["review"]["current_status"] = "final_review"
    status_path.write_text(yaml.safe_dump(status))
    store.submit(
        SOURCE,
        {
            "kind": "approve",
            "subject_id": "statement",
            "expected_etag": etag(document),
            "review_digest": material(document),
        },
    )
    page = render_review_html(store.root, store.session_id)
    assert "<summary>Panel confirmation of reviewed transactions</summary>" in page
    assert "approved_at" in page
    assert "panel" in page
    assert "Ledger validation is not available yet" in page
    assert "actions" not in store.statement(SOURCE)["review"]


def test_export_price_details_and_tool_contract(review_store: ReviewFiles) -> None:
    store = review_store
    run = {
        "run_id": "price-1",
        "requested_date": "2026-01-31",
        "state": "complete",
        "required_commodities": ["STOCK"],
        "coverage": ["STOCK"],
        "preflight": "passed",
        "preflight_job_count": 1,
        "execution": {
            "state": "complete",
            "exit_code": 0,
            "duration_seconds": 0.2,
            "stderr_summary": "",
        },
        "jobs": [
            {
                "commodity": "STOCK",
                "source": "fixture",
                "requested_date": "2026-01-31",
                "quote_date": "2026-01-30",
                "outcome": "emitted",
                "directive": "2026-01-30 price STOCK 20 EUR",
            }
        ],
        "detail": "Known quote result",
    }
    session = store.read(store.session_path)
    session["price_runs"] = [run]
    (store.root / store.session_path).write_text(json.dumps(session))
    result = dispatch(
        "export_import_review",
        {"workspace": str(store.root), "session_id": store.session_id},
    )
    validate(
        output_schema(CONTRACTS["export_import_review"][1]),
        {"status": "ok", "result": result},
    )
    page = Path(result["path"]).read_text()
    assert "2026-01-30 price STOCK 20 EUR" in page
    assert "Known quote result" in page
    assert "2026-01-31" in page
    assert "emitted" in page


def test_export_refuses_symlink_destination(
    review_store: ReviewFiles, tmp_path: Path
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (review_store.root / ".auto-bean/exports").symlink_to(
        outside, target_is_directory=True
    )
    with pytest.raises(WorkflowError, match="symlink"):
        export_review_html(review_store.root, review_store.session_id)
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("changed_path", ["ledger.beancount", SOURCE])
def test_export_and_panel_mark_recorded_validation_stale_after_ledger_edit(
    review_store: ReviewFiles,
    changed_path: str,
) -> None:
    from auto_bean.reconciliation import validate_import
    from test_review import approve, ledger_transaction

    store = review_store
    complete(store)
    approve(store)
    ledger = store.root / "ledger.beancount"
    ledger.write_text(BASE + ledger_transaction(store))
    assert validate_import(store.root, store.session_id)["state"] == "passed"
    args = {
        "workspace": str(store.root),
        "session_id": store.session_id,
        "source_file": SOURCE,
    }
    assert dispatch("read_import_statement", args)["validation_current"] is True
    original = store.statement(SOURCE)
    changed = store.root / changed_path
    changed.write_text(changed.read_text() + "\n; Later user edit\n")
    assert dispatch("read_import_statement", args)["validation_current"] is False
    page = render_review_html(store.root, store.session_id)
    assert "Stale validation: the current ledger" in page
    assert store.statement(SOURCE) == original


def test_export_separates_review_readiness_from_ledger_write_validation(
    review_store: ReviewFiles,
) -> None:
    from auto_bean.reconciliation import validate_import

    complete(review_store)
    result = validate_import(review_store.root, review_store.session_id, stage="review")
    assert result["state"] == "passed"
    page = render_review_html(review_store.root, review_store.session_id)
    assert "Review readiness validation (does not confirm ledger writes)" in page
    assert "<summary>Ledger write validation</summary>" not in page
    assert "Approval can also be given in conversation" in page


def test_export_rejects_direct_edit_during_snapshot(
    review_store: ReviewFiles, monkeypatch: pytest.MonkeyPatch
) -> None:
    complete(review_store)
    original = ReviewFiles.check_links

    def edit_during_read(self: ReviewFiles, sources: list[str] | None = None) -> None:
        original(self, sources)
        document = self.statement(SOURCE)
        document["review"]["processing"]["warnings"].append("Concurrent agent edit")
        save(self, PARSED, document)

    monkeypatch.setattr(ReviewFiles, "check_links", edit_during_read)
    with pytest.raises(WorkflowError, match="changed during export"):
        export_review_html(review_store.root, review_store.session_id)
    assert not list((review_store.root / ".auto-bean/exports").glob("*.html"))


def test_peer_edit_marks_local_transfer_validation_stale(
    review_store: ReviewFiles,
) -> None:
    from auto_bean.reconciliation import validate_import

    store = review_store
    document = complete(store)
    peer_source = "statements/raw/savings.csv"
    (store.root / peer_source).write_text("date,amount\n2026-01-02,25\n")
    peer_fingerprint = "sha256:" + digest((store.root / peer_source).read_bytes())
    (store.root / "ledger.beancount").write_text(
        BASE + "2025-01-01 open Assets:Savings EUR\n"
    )
    row = document["extracted_records"][0]
    row["description"] = "Transfer"
    row["review"].update(
        disposition="paired_transfer",
        posting_owner=SOURCE,
        postings=[
            {"account": "Assets:Checking", "amount": "-25", "currency": "EUR"},
            {"account": "Assets:Savings", "amount": "25", "currency": "EUR"},
        ],
        linked_records=[
            {"source_file": peer_source, "account_id": "savings", "record_id": "row-1"}
        ],
    )
    peer = copy.deepcopy(document)
    peer.update(source_file=peer_source, source_fingerprint=peer_fingerprint)
    peer["statement_metadata"]["accounts"][0].update(
        account_id="savings", account_name="Savings"
    )
    peer["statement_metadata"]["accounts"][0]["review"]["ledger_account"] = (
        "Assets:Savings"
    )
    peer_row = peer["extracted_records"][0]
    peer_row.update(account_id="savings", amount="25")
    peer_row["review"].update(
        postings=[],
        linked_records=[
            {"source_file": SOURCE, "account_id": "checking", "record_id": "row-1"}
        ],
    )
    save(store, PARSED, document)
    save(store, PARSED, peer)
    session = store.read(store.session_path)
    session["groups"][0]["source_files"].append(peer_source)
    (store.root / store.session_path).write_text(json.dumps(session))
    status_path = store.root / "statements/import-status.yml"
    status = yaml.safe_load(status_path.read_text())
    status["groups"]["review"]["sources"][peer_source] = {
        "source_fingerprint": peer_fingerprint
    }
    status_path.write_text(yaml.safe_dump(status))
    assert (
        validate_import(store.root, store.session_id, stage="review")["state"]
        == "passed"
    )
    args = {
        "workspace": str(store.root),
        "session_id": store.session_id,
        "source_file": SOURCE,
    }
    assert dispatch("read_import_statement", args)["validation_current"] is True
    peer = store.statement(peer_source)
    peer["extracted_records"][0]["description"] = "Corrected transfer evidence"
    save(store, PARSED, peer)
    assert dispatch("read_import_statement", args)["validation_current"] is False
    assert "Stale validation: the current ledger" in render_review_html(
        store.root, store.session_id
    )


def test_export_displays_saved_statement_groups(review_store: ReviewFiles) -> None:
    session = review_store.read(review_store.session_path)
    session["groups"][0].update(name="January <accounts>", origin="user")
    (review_store.root / review_store.session_path).write_text(json.dumps(session))
    page = render_review_html(review_store.root, review_store.session_id)
    assert "Statement groups" in page
    assert "January &lt;accounts&gt;" in page
    assert "User-defined" in page
