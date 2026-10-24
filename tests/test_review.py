from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from auto_bean import reconciliation
from auto_bean.common import WorkflowError, atomic_write, digest
from auto_bean.review import (
    ReviewFiles,
    etag,
    account_decisions,
    transaction_decisions,
    material,
    now,
)
from auto_bean.validation import validate_state

SOURCE = "statements/raw/review.csv"
PARSED = "statements/parsed/review.json"
BASE = """option "operating_currency" "EUR"
2025-01-01 open Assets:Checking EUR
2025-01-01 open Expenses:Food EUR
"""
TX = """\n2026-01-02 * "Market"
  source: "review.csv:row:1"
  Assets:Checking -25 EUR
  Expenses:Food 25 EUR
"""


def save(store: ReviewFiles, path: str, document: dict[str, Any]) -> None:
    target = store.root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    if "source_file" in document:
        group = (
            json.loads(target.read_text())
            if target.exists()
            else {"schema_version": 2, "group_id": "review", "statements": []}
        )
        group["statements"] = [
            d
            for d in group["statements"]
            if d["source_file"] != document["source_file"]
        ] + [document]
        document = group
    target.write_text(json.dumps(document, indent=2) + "\n")


def validate(store: ReviewFiles, stage: str = "written") -> dict[str, Any]:
    return dict(
        reconciliation.validate_import(store.root, store.session_id, stage)[
            "statements"
        ][SOURCE]
    )


@pytest.fixture
def review_store(current: Path) -> ReviewFiles:
    (current / "ledger.beancount").write_text(BASE)
    atomic_write(current / SOURCE, b"date,amount\n2026-01-02,-25\n")
    fingerprint = "sha256:" + digest((current / SOURCE).read_bytes())
    status = {
        "version": 1,
        "groups": {
            "review": {
                "session_id": "test-session",
                "current_status": "raw_ready",
                "parsed_group": PARSED,
                "sources": {SOURCE: {"source_fingerprint": fingerprint}},
            }
        },
    }
    (current / "statements/import-status.yml").write_text(yaml.safe_dump(status))
    store = ReviewFiles(current, "test-session")
    save(
        store,
        store.session_path,
        {
            "schema_version": 1,
            "session_id": "test-session",
            "created_at": now(),
            "groups": [
                {
                    "group_id": "review",
                    "parsed_group": PARSED,
                    "name": "Review",
                    "origin": "agent",
                    "source_files": [SOURCE],
                }
            ],
            "price_runs": [],
        },
    )
    save(
        store,
        PARSED,
        {
            "schema_version": 2,
            "source_file": SOURCE,
            "source_fingerprint": fingerprint,
            "source_format": "csv",
            "extraction_state": "pending",
            "statement_metadata": {"accounts": []},
            "extracted_records": [],
            "review": {
                "processing": {
                    "attempts": 0,
                    "outcome": "pending",
                    "warnings": [],
                    "evidence": [],
                }
            },
        },
    )
    return store


def complete(store: ReviewFiles) -> dict[str, Any]:
    doc = store.statement(SOURCE)
    doc.update(
        extraction_state="complete",
        parse_run_id="parse-1",
        parsed_at=now(),
        parser={"name": "csv"},
        document_kind="statement",
        statement_metadata={
            "accounts": [
                {
                    "account_id": "checking",
                    "account_name": "Checking",
                    "review": {
                        "state": "confirmed",
                        "ledger_account": "Assets:Checking",
                        "rationale": "User account",
                    },
                }
            ]
        },
        extracted_records=[
            {
                "record_id": "row-1",
                "source_reference": "row:1",
                "account_id": "checking",
                "transaction_date": "2026-01-02",
                "description": "Market",
                "amount": "-25",
                "currency": "EUR",
                "review": {
                    "state": "proposed",
                    "postings": [
                        {
                            "account": "Assets:Checking",
                            "amount": "-25",
                            "currency": "EUR",
                        },
                        {"account": "Expenses:Food", "amount": "25", "currency": "EUR"},
                    ],
                    "rationale": "Market receipt",
                    "findings": [],
                    "disposition": "post",
                    "linked_records": [],
                },
            }
        ],
    )
    save(store, PARSED, doc)
    return doc


def approve(store: ReviewFiles) -> dict[str, Any]:
    doc = store.statement(SOURCE)
    return store.submit(
        SOURCE,
        {
            "kind": "approve",
            "subject_id": "statement",
            "expected_etag": etag(doc),
            "review_digest": material(doc),
        },
    )


def ledger_transaction(store: ReviewFiles) -> str:
    return f'''\n2026-01-02 * "Market"
  source: "{SOURCE}"
  source_fingerprint: "{store.statement(SOURCE)["source_fingerprint"]}"
  account_id: "checking"
  record_id: "row-1"
  Assets:Checking -25 EUR
  Expenses:Food 25 EUR
'''


def set_status(store: ReviewFiles, value: str) -> None:
    path = store.root / "statements/import-status.yml"
    status = yaml.safe_load(path.read_text())
    status["groups"]["review"]["current_status"] = value
    path.write_text(yaml.safe_dump(status))


def final_review(store: ReviewFiles) -> None:
    path = store.root / "statements/import-status.yml"
    text = path.read_text().replace("raw_ready", "final_review")
    path.write_text(text)


def test_parsed_is_only_transaction_write_input(review_store: ReviewFiles) -> None:
    store = review_store
    complete(store)
    baseline = (store.root / "ledger.beancount").read_bytes()
    approved = approve(store)
    assert set(store.read(store.session_path)) == {
        "schema_version",
        "session_id",
        "created_at",
        "price_runs",
        "groups",
    }
    assert set(store.statement(SOURCE)["review"]) == {"processing", "approval"}
    assert approved["review_digest"] == material(store.statement(SOURCE))
    assert (store.root / "ledger.beancount").read_bytes() == baseline
    # The Write skill edits the ledger directly; validation never creates postings.
    assert validate(store)["state"] == "failed"
    assert (store.root / "ledger.beancount").read_bytes() == baseline
    (store.root / "ledger.beancount").write_text(BASE + ledger_transaction(store))
    report = validate(store)
    assert report["state"] == "passed", report
    assert report["records_checked"] == 1
    assert report["balances"] == []  # Missing balances are not invented.
    assert validate(store) == report
    final_review(store)
    assert validate(store)["state"] == "passed"
    set_status(store, "done")
    assert (store.root / "ledger.beancount").read_text().count(
        'record_id: "row-1"'
    ) == 1


def test_confirmation_is_current_and_corrections_require_review(
    review_store: ReviewFiles,
) -> None:
    store = review_store
    complete(store)
    approve(store)
    doc = store.statement(SOURCE)
    original = material(doc)
    stale = {
        "kind": "approve",
        "subject_id": "statement",
        "expected_etag": etag(doc),
        "review_digest": original,
    }
    doc["review"]["processing"]["warnings"].append("Harmless progress")
    save(store, PARSED, doc)
    assert material(doc) == original
    with pytest.raises(WorkflowError, match="Review changed"):
        store.submit(SOURCE, stale)
    result = store.submit(
        SOURCE,
        {
            "kind": "mapping",
            "subject_id": "checking",
            "expected_etag": etag(doc),
            "value": "Assets:Savings",
        },
    )
    changed = store.statement(SOURCE)
    assert result["etag"] == etag(changed)
    assert "approval" not in changed["review"]
    assert account_decisions(changed)["checking"]["state"] == "needs_input"
    stale["expected_etag"] = etag(changed)
    with pytest.raises(WorkflowError, match="transactions changed"):
        store.submit(SOURCE, stale)
    with pytest.raises(WorkflowError):
        approve(store)


def test_no_action_log_rejection_and_retry_conflict(review_store: ReviewFiles) -> None:
    store = review_store
    doc = complete(store)
    update = {
        "kind": "answer",
        "subject_id": "row-1",
        "subject_kind": "transaction",
        "expected_etag": etag(doc),
        "value": "Meal receipt verified",
    }
    store.submit(SOURCE, update)
    with pytest.raises(WorkflowError, match="Review changed"):
        store.submit(SOURCE, update)
    doc = store.statement(SOURCE)
    assert transaction_decisions(doc)["row-1"]["answer"] == "Meal receipt verified"
    decision = copy.deepcopy(transaction_decisions(doc)["row-1"])
    decision["state"] = "confirmed"
    transaction_decisions(doc)["row-1"].update(decision)
    save(store, PARSED, doc)
    approve(store)
    doc = store.statement(SOURCE)
    store.submit(
        SOURCE,
        {
            "kind": "reject",
            "subject_id": "statement",
            "expected_etag": etag(doc),
            "review_digest": material(doc),
        },
    )
    assert "approval" not in store.statement(SOURCE)["review"]
    assert (store.root / "ledger.beancount").read_text() == BASE


@pytest.mark.parametrize(
    "failure",
    [
        "missing",
        "duplicate",
        "amount",
        "category",
        "date",
        "provenance",
        "extra_record",
    ],
)
def test_validation_rejects_wrong_or_missing_rows(
    review_store: ReviewFiles, failure: str
) -> None:
    store = review_store
    complete(store)
    approve(store)
    tx = ledger_transaction(store)
    ledger = BASE + tx
    if failure == "missing":
        ledger = BASE
    elif failure == "duplicate":
        ledger += tx
    elif failure == "amount":
        ledger = ledger.replace("25 EUR", "24 EUR")
    elif failure == "category":
        ledger = ledger.replace("Expenses:Food", "Expenses:Other")
    elif failure == "date":
        ledger = ledger.replace("2026-01-02", "2026-01-03")
    elif failure == "provenance":
        ledger = ledger.replace('account_id: "checking"', 'account_id: "different"')
    else:
        ledger += tx.replace('record_id: "row-1"', 'record_id: "unknown"')
    (store.root / "ledger.beancount").write_text(ledger)
    before = (store.root / "ledger.beancount").read_bytes()
    report = validate(store)
    assert report["state"] == "failed" and report["errors"]
    assert (store.root / "ledger.beancount").read_bytes() == before


def test_validation_does_not_trust_fabricated_pass(review_store: ReviewFiles) -> None:
    store = review_store
    complete(store)
    (store.root / "ledger.beancount").write_text(BASE + ledger_transaction(store))
    report = validate(store)
    assert report["state"] == "passed"
    (store.root / "ledger.beancount").write_text(BASE)
    assert validate(store)["state"] == "failed"
    doc = store.statement(SOURCE)
    doc["review"]["validation"] = report
    save(store, PARSED, doc)
    assert validate(store)["state"] == "failed"
    assert (store.root / "ledger.beancount").read_text() == BASE


@pytest.mark.parametrize("expected,state", [("-25", "passed"), ("0", "failed")])
def test_closing_balance_at_statement_date(
    review_store: ReviewFiles, expected: str, state: str
) -> None:
    store = review_store
    complete(store)
    doc = store.statement(SOURCE)
    doc["statement_metadata"]["accounts"][0]["closing_balance"] = {
        "date": "2026-01-02",
        "amount": expected,
        "currency": "EUR",
    }
    save(store, PARSED, doc)
    approve(store)
    later = (
        '\n2026-01-03 * "Later"\n  Assets:Checking -10 EUR\n  Expenses:Food 10 EUR\n'
    )
    (store.root / "ledger.beancount").write_text(
        BASE + ledger_transaction(store) + later
    )
    report = validate(store)
    assert report["state"] == state, report
    assert report["balances"][0]["actual"] == "-25"


def test_equal_balance_cannot_hide_offsetting_missing_rows(
    review_store: ReviewFiles,
) -> None:
    store = review_store
    complete(store)
    doc = store.statement(SOURCE)
    first = doc["extracted_records"][0]
    second = copy.deepcopy(first)
    second.update(record_id="refund", source_reference="row:2", amount="25")
    for posting in second["review"]["postings"]:
        posting["amount"] = str(-int(posting["amount"]))
    doc["extracted_records"].append(second)
    doc["statement_metadata"]["accounts"][0]["closing_balance"] = {
        "date": "2026-01-02",
        "amount": "0",
        "currency": "EUR",
    }
    save(store, PARSED, doc)
    approve(store)
    report = validate(store)
    assert report["balances"][0]["state"] == "matched"
    assert report["state"] == "failed" and report["records_checked"] == 0


def test_existing_duplicate_checks_exact_postings_after_append(
    review_store: ReviewFiles,
) -> None:
    store = review_store
    complete(store)
    existing = (
        '\n2026-01-02 * "Market"\n  Assets:Checking -25 EUR\n  Expenses:Food 25 EUR\n'
    )
    (store.root / "ledger.beancount").write_text(BASE + existing)
    doc = store.statement(SOURCE)
    decision = transaction_decisions(doc)["row-1"]
    decision.update(
        disposition="existing_duplicate",
        existing_transaction={"path": "ledger.beancount", "line": 5},
    )
    save(store, PARSED, doc)
    approve(store)
    report = validate(store)
    assert report["state"] == "passed", report
    (store.root / "ledger.beancount").write_text(
        BASE + existing + "\n; unrelated appended note\n"
    )
    assert validate(store)["state"] == "passed"
    (store.root / "ledger.beancount").write_text(
        BASE + existing.replace("25 EUR", "26 EUR")
    )
    assert validate(store)["state"] == "failed"


def test_raw_source_change_invalidates_review(review_store: ReviewFiles) -> None:
    store = review_store
    complete(store)
    approve(store)
    (store.root / "ledger.beancount").write_text(BASE + ledger_transaction(store))
    (store.root / SOURCE).write_text("changed source")
    assert validate(store)["state"] == "failed"
    with pytest.raises(WorkflowError, match="Raw source changed"):
        approve(store)


def test_schema_removes_execution_records(review_store: ReviewFiles) -> None:
    store = review_store
    doc = complete(store)
    for key in ("actions", "memory", "candidates", "candidate_refs"):
        changed = copy.deepcopy(doc)
        changed["review"][key] = []
        with pytest.raises(WorkflowError):
            validate_state("parsed", store.root, changed)
    for key in ("changes", "actions"):
        session = store.read(store.session_path)
        session[key] = []
        with pytest.raises(WorkflowError):
            validate_state("session", store.root, session)


def test_financial_path_checks_do_not_follow_symlinks(
    review_store: ReviewFiles, tmp_path: Path
) -> None:
    store = review_store
    outside = tmp_path / "secret.beancount"
    outside.write_text(BASE)
    (store.root / "beancount/linked.beancount").symlink_to(outside)
    with pytest.raises(WorkflowError, match="symlink"):
        reconciliation.financial_files(store.root)


def test_done_blocks_in_place_corrections(review_store: ReviewFiles) -> None:
    store = review_store
    complete(store)
    approve(store)
    (store.root / "ledger.beancount").write_text(BASE + ledger_transaction(store))
    final_review(store)
    assert validate(store)["state"] == "passed"
    set_status(store, "done")
    doc = store.statement(SOURCE)
    with pytest.raises(WorkflowError, match="Completed"):
        store.submit(
            SOURCE,
            {
                "kind": "mapping",
                "subject_id": "checking",
                "expected_etag": etag(doc),
                "value": "Assets:Other",
            },
        )


def test_partial_strict_schema(review_store: ReviewFiles) -> None:
    store = review_store
    doc = store.statement(SOURCE)
    assert doc["extraction_state"] == "pending"
    for mutate in ("unknown", "date", "decimal", "cross_ref", "revision"):
        changed = copy.deepcopy(complete(store) if mutate != "unknown" else doc)
        if mutate == "unknown":
            changed["garbage"] = True
        elif mutate == "date":
            changed["extracted_records"][0]["transaction_date"] = "2026-02-30"
        elif mutate == "decimal":
            changed["extracted_records"][0]["amount"] = 25
        elif mutate == "cross_ref":
            changed["extracted_records"][0]["account_id"] = "absent"
        else:
            changed["revision"] = 0
        with pytest.raises(WorkflowError):
            validate_state("parsed", store.root, changed)


def test_schema_detects_crossed_record_reference(review_store: ReviewFiles) -> None:
    document = complete(review_store)
    document["statement_metadata"]["accounts"].append({"account_id": "other"})
    transaction_decisions(document)["row-1"]["linked_records"] = [
        {"source_file": SOURCE, "account_id": "other", "record_id": "row-1"}
    ]
    with pytest.raises(WorkflowError, match="Linked record"):
        validate_state("parsed", review_store.root, document)


def test_tampered_session_identity_is_rejected(review_store: ReviewFiles) -> None:
    session = review_store.read(review_store.session_path)
    session["session_id"] = "wrong-session"
    save(review_store, review_store.session_path, session)
    with pytest.raises(WorkflowError, match="identity"):
        review_store.read(review_store.session_path)


def test_status_pointer_changes_block_panel_mutations(
    review_store: ReviewFiles,
) -> None:
    doc = complete(review_store)
    path = review_store.root / "statements/import-status.yml"
    status = yaml.safe_load(path.read_text())
    status["groups"]["review"]["parsed_group"] = "statements/parsed/different.json"
    path.write_text(yaml.safe_dump(status))
    with pytest.raises(WorkflowError, match="membership"):
        review_store.submit(
            SOURCE,
            {
                "kind": "mapping",
                "subject_id": "checking",
                "expected_etag": etag(doc),
                "value": "Assets:Other",
            },
        )
    assert (
        reconciliation.validate_import(review_store.root, review_store.session_id)[
            "state"
        ]
        == "failed"
    )


def test_concurrent_panel_updates_cannot_overwrite_each_other(
    review_store: ReviewFiles,
) -> None:
    from concurrent.futures import ThreadPoolExecutor

    doc = complete(review_store)

    def attempt(value: str) -> str:
        try:
            review_store.submit(
                SOURCE,
                {
                    "kind": "answer",
                    "subject_kind": "transaction",
                    "subject_id": "row-1",
                    "expected_etag": etag(doc),
                    "value": value,
                },
            )
            return "saved"
        except WorkflowError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, ["worker-a", "worker-b"]))
    assert sorted(outcomes) == ["edit_conflict", "saved"]


@pytest.mark.parametrize(
    "outcome", ["no_op", "complete", "partial", "failed", "timeout"]
)
def test_deterministic_price_terminal_outcomes(
    review_store: ReviewFiles, outcome: str
) -> None:
    run: dict[str, Any] = {
        "run_id": "price-1",
        "requested_date": "2026-01-31",
        "state": "no_op" if outcome == "no_op" else "complete",
        "required_commodities": [] if outcome == "no_op" else ["STOCK"],
        "coverage": [] if outcome == "no_op" else ["STOCK"],
        "preflight": "passed",
        "preflight_job_count": 0 if outcome == "no_op" else 1,
        "jobs": []
        if outcome == "no_op"
        else [
            {
                "commodity": "STOCK",
                "source": "fixture",
                "requested_date": "2026-01-31",
                "quote_date": "2026-01-30",
                "outcome": "emitted",
                "directive": "2026-01-30 price STOCK 20 EUR",
            }
        ],
        "detail": "Deterministic fixture result",
        "execution": {
            "state": "complete",
            "exit_code": 0,
            "duration_seconds": 0.1,
            "stderr_summary": "",
        },
    }
    if outcome == "partial":
        run.update(state="partial", coverage=[])
        run["jobs"][0]["outcome"] = "unaccounted"
    if outcome == "failed":
        run.update(state="failed")
        run["execution"]["exit_code"] = 1
        run["jobs"][0]["outcome"] = "failed"
    if outcome == "timeout":
        run.update(state="failed")
        run["execution"].update(state="timed_out", exit_code=None)
        run["jobs"][0]["outcome"] = "unaccounted"
    session = review_store.read(review_store.session_path)
    session["price_runs"] = [run]
    validate_state("session", review_store.root, session)
    save(review_store, review_store.session_path, session)
    if outcome != "no_op":
        run["state"] = "complete"
        run["execution"].update(state="complete", exit_code=0)
        run["coverage"] = []
        with pytest.raises(WorkflowError):
            session["price_runs"] = [run]
            validate_state("session", review_store.root, session)


@pytest.mark.parametrize("field", ["account_id", "record_id"])
def test_extracted_identifiers_must_be_usable_as_review_keys(
    review_store: ReviewFiles, field: str
) -> None:
    document = complete(review_store)
    if field == "account_id":
        document["statement_metadata"]["accounts"][0][field] = "bad/account"
    else:
        document["extracted_records"][0][field] = "bad/record"
    with pytest.raises(WorkflowError, match="Schema violation"):
        validate_state("parsed", review_store.root, document)


def test_partial_prices_cannot_hide_unaccounted_jobs(review_store: ReviewFiles) -> None:
    run = {
        "run_id": "partial",
        "requested_date": "2026-01-31",
        "state": "partial",
        "required_commodities": ["STOCK"],
        "coverage": [],
        "preflight": "passed",
        "preflight_job_count": 1,
        "jobs": [],
        "detail": "Provider timed out",
        "execution": {
            "state": "timed_out",
            "exit_code": None,
            "duration_seconds": 180,
            "stderr_summary": "Timeout",
        },
    }
    session = review_store.read(review_store.session_path)
    session["price_runs"] = [run]
    with pytest.raises(WorkflowError, match="every preflight job"):
        validate_state("session", review_store.root, session)


@pytest.mark.parametrize("field", ["description", "payee"])
def test_written_narration_and_payee_follow_source(
    review_store: ReviewFiles, field: str
) -> None:
    store = review_store
    doc = complete(store)
    if field == "payee":
        doc["extracted_records"][0]["payee"] = "Example Market"
        save(store, PARSED, doc)
    approve(store)
    tx = ledger_transaction(store)
    if field == "description":
        tx = tx.replace('* "Market"', '* "Another purchase"')
    (store.root / "ledger.beancount").write_text(BASE + tx)
    result = validate(store)
    assert result["state"] == "failed"
    assert any("narration" in e or "payee" in e for e in result["errors"])


def test_required_supporting_directives_are_validated(
    review_store: ReviewFiles,
) -> None:
    store = review_store
    doc = complete(store)
    account_decisions(doc)["checking"]["proposed_directives"] = [
        "2025-01-01 open Assets:Reserve EUR",
        "2026-01-03 balance Assets:Checking -25 EUR",
    ]
    save(store, PARSED, doc)
    approve(store)
    ledger = BASE + ledger_transaction(store)
    (store.root / "ledger.beancount").write_text(ledger)
    result = validate(store)
    assert result["state"] == "failed"
    assert sum("supporting directive" in e for e in result["errors"]) == 2
    ledger += "\n2025-01-01 open Assets:Reserve EUR\n2026-01-03 balance Assets:Checking -25 EUR\n"
    (store.root / "ledger.beancount").write_text(ledger)
    assert validate(store)["state"] == "passed"


def test_split_postings_cannot_be_collapsed_even_when_balanced(
    review_store: ReviewFiles,
) -> None:
    store = review_store
    doc = complete(store)
    decision = transaction_decisions(doc)["row-1"]
    decision["postings"][1]["amount"] = "20"
    decision["postings"].append(
        {"account": "Expenses:Other", "amount": "5", "currency": "EUR"}
    )
    save(store, PARSED, doc)
    approve(store)
    ledger = BASE + "2025-01-01 open Expenses:Other EUR\n" + ledger_transaction(store)
    (store.root / "ledger.beancount").write_text(ledger)
    assert validate(store)["state"] == "failed"
    ledger = ledger.replace(
        "  Expenses:Food 25 EUR", "  Expenses:Food 20 EUR\n  Expenses:Other 5 EUR"
    )
    (store.root / "ledger.beancount").write_text(ledger)
    assert validate(store)["state"] == "passed"


@pytest.mark.parametrize("price_only", [False, True])
def test_price_panel_confirmation_does_not_replace_actual_write(
    review_store: ReviewFiles, price_only: bool
) -> None:
    from auto_bean.review import price_material

    store = review_store

    def price_report() -> dict[str, Any]:
        result = reconciliation.validate_import(
            store.root, store.session_id, price_run_id="fx" if price_only else None
        )
        return dict(result["prices"]["fx"])

    run = {
        "run_id": "fx",
        "requested_date": "2026-01-31",
        "state": "complete",
        "required_commodities": ["USD"],
        "coverage": ["USD"],
        "preflight": "passed",
        "preflight_job_count": 1,
        "execution": {
            "state": "complete",
            "exit_code": 0,
            "duration_seconds": 0.1,
            "stderr_summary": "",
        },
        "jobs": [
            {
                "commodity": "USD",
                "source": "synthetic",
                "requested_date": "2026-01-31",
                "quote_date": "2026-01-30",
                "outcome": "emitted",
                "directive": "2026-01-30 price USD 0.92 EUR",
            }
        ],
        "detail": "Synthetic test only",
    }
    complete(store)
    session = store.read(store.session_path)
    session["price_runs"] = [run]
    save(store, store.session_path, session)
    assert price_report()["state"] == "failed"

    session = store.read(store.session_path)
    store.approve_prices("fx", etag(session), price_material(run))
    assert price_report()["state"] == "failed"
    (store.root / "ledger.beancount").write_text(
        BASE + "\n2026-01-30 price USD 0.92 EUR\n"
    )
    report = price_report()
    assert report["state"] == "passed"
    assert report["records_checked"] == 1
    assert price_report() == report
    session = store.read(store.session_path)
    run = session["price_runs"][0]
    run["jobs"][0]["directive"] = "2026-01-30 price USD 0.95 EUR"
    save(store, store.session_path, session)
    assert run["approval"]["digest"] != price_material(run)
    assert price_report()["state"] == "failed"


@pytest.mark.parametrize("broken_ledger", [False, True])
def test_price_only_validation_preserves_blocked_statement_review(
    review_store: ReviewFiles, broken_ledger: bool
) -> None:
    store = review_store
    doc = complete(store)
    row = doc["extracted_records"][0]["review"]
    row.update(state="needs_input", disposition="hold", postings=[])
    save(store, PARSED, doc)
    review = validate(store, "review")
    assert review["state"] == "failed"
    before = (store.root / PARSED).read_bytes()
    status_before = (store.root / "statements/import-status.yml").read_bytes()
    session = store.read(store.session_path)
    run = {
        "run_id": "no-prices",
        "requested_date": "2026-01-31",
        "state": "no_op",
        "required_commodities": [],
        "coverage": [],
        "preflight": "passed",
        "preflight_job_count": 0,
        "jobs": [],
        "detail": "No required commodities",
        "execution": {
            "state": "complete",
            "exit_code": 0,
            "duration_seconds": 0,
            "stderr_summary": "",
        },
    }
    other = dict(run, run_id="other")
    session["price_runs"] = [run, other]
    save(store, store.session_path, session)
    ledger = store.root / "ledger.beancount"
    if broken_ledger:
        ledger.write_text(BASE + "\n2026-01-02 balance Assets:Checking 100 EUR\n")
    ledger_before = ledger.read_bytes()
    report = reconciliation.validate_import(
        store.root, store.session_id, price_run_id="no-prices"
    )
    assert report["state"] == ("failed" if broken_ledger else "passed"), report
    assert report["statements"] == report["groups"] == {}
    assert set(report["prices"]) == {"no-prices"}
    assert report["prices"]["no-prices"]["stage"] == "written"
    assert (store.root / PARSED).read_bytes() == before
    assert (store.root / "statements/import-status.yml").read_bytes() == status_before
    assert store.read(store.session_path)["price_runs"][1] == other
    assert ledger.read_bytes() == ledger_before
    # A normal session check still reports the statement's unresolved decisions.
    assert (
        reconciliation.validate_import(store.root, store.session_id, "review")["state"]
        == "failed"
    )


@pytest.mark.parametrize("session", [None, "test-session"])
def test_invalid_price_scope_does_not_publish_reports(
    review_store: ReviewFiles, session: str | None
) -> None:
    store = review_store
    before = (store.root / PARSED).read_bytes()
    session_before = (store.root / store.session_path).read_bytes()
    result = reconciliation.validate_import(store.root, session, price_run_id="unknown")
    assert result["state"] == "failed"
    assert result["errors"]
    assert (store.root / PARSED).read_bytes() == before
    assert (store.root / store.session_path).read_bytes() == session_before


def test_document_directive_is_resolved_from_workspace(
    review_store: ReviewFiles,
) -> None:
    store = review_store
    doc = complete(store)
    directive = f'2026-01-31 document Assets:Checking "{SOURCE}"'
    account_decisions(doc)["checking"]["proposed_directives"] = [directive]
    save(store, PARSED, doc)
    approve(store)
    ledger = BASE + ledger_transaction(store)
    (store.root / "ledger.beancount").write_text(ledger)
    assert validate(store)["state"] == "failed"
    (store.root / "ledger.beancount").write_text(ledger + "\n" + directive + "\n")
    result = validate(store)
    assert result["state"] == "passed", result


def test_regular_transaction_cannot_hide_another_source_identity(
    review_store: ReviewFiles,
) -> None:
    store = review_store
    complete(store)
    approve(store)
    tx = ledger_transaction(store).replace(
        '  account_id: "checking"',
        '  peer_source: "statements/raw/other.csv"\n  peer_source_fingerprint: "sha256:'
        + "0" * 64
        + '"\n  peer_account_id: "other"\n  peer_record_id: "another"\n  account_id: "checking"',
    )
    (store.root / "ledger.beancount").write_text(BASE + tx)
    result = validate(store)
    assert result["state"] == "failed"
    assert any("only its own source row" in error for error in result["errors"])


def test_review_and_written_validation_do_not_require_panel_approval(
    review_store: ReviewFiles,
) -> None:
    store = review_store
    complete(store)
    before = (store.root / "ledger.beancount").read_bytes()
    reviewed = validate(store, "review")
    assert reviewed["state"] == "passed"
    assert reviewed["stage"] == "review"
    assert "approval" not in store.statement(SOURCE)["review"]
    assert (store.root / "ledger.beancount").read_bytes() == before
    assert validate(store)["state"] == "failed"
    (store.root / "ledger.beancount").write_text(BASE + ledger_transaction(store))
    written = validate(store)
    assert written["state"] == "passed"
    assert written["stage"] == "written"
    assert written["digest"] == reviewed["digest"]
    assert "approval" not in store.statement(SOURCE)["review"]
    assert validate(store) == written


@pytest.mark.parametrize("completed_status", ["final_review", "done"])
@pytest.mark.parametrize("remove_transaction", [False, True])
def test_review_of_new_group_rechecks_completed_evidence(
    review_store: ReviewFiles, completed_status: str, remove_transaction: bool
) -> None:
    store = review_store
    complete(store)
    approve(store)
    ledger = store.root / "ledger.beancount"
    ledger.write_text(BASE + ledger_transaction(store))
    written = validate(store)
    assert written["state"] == "passed"
    set_status(store, completed_status)
    completed_bytes = (store.root / PARSED).read_bytes()
    approval = store.statement(SOURCE)["review"]["approval"]

    # A new statement joins this session after the first one was written.
    source = "statements/raw/new.csv"
    parsed = "statements/parsed/new.json"
    (store.root / source).write_text("new statement")
    doc = copy.deepcopy(store.statement(SOURCE))
    doc["source_file"] = source
    doc["source_fingerprint"] = "sha256:" + digest((store.root / source).read_bytes())
    doc["review"].pop("validation")
    doc["review"].pop("approval")
    session = store.read(store.session_path)
    session["groups"].append(
        {
            "group_id": "new",
            "name": "New statement",
            "origin": "agent",
            "source_files": [source],
            "parsed_group": parsed,
        }
    )
    save(store, store.session_path, session)
    status_path = store.root / "statements/import-status.yml"
    status = yaml.safe_load(status_path.read_text())
    status["groups"]["new"] = {
        "session_id": store.session_id,
        "current_status": "final_review",
        "parsed_group": parsed,
        "sources": {source: {"source_fingerprint": doc["source_fingerprint"]}},
    }
    status_path.write_text(yaml.safe_dump(status))
    save(store, parsed, {"schema_version": 2, "group_id": "new", "statements": [doc]})
    if remove_transaction:
        ledger.write_text(BASE)
    ledger_before = ledger.read_bytes()
    result = reconciliation.validate_import(store.root, store.session_id, "review")
    assert result["statements"][source]["stage"] == "review"
    assert result["statements"][source]["state"] == "passed"
    assert result["groups"]["new"]["stage"] == "review"
    assert result["statements"][SOURCE]["stage"] == "written"
    assert result["groups"]["review"]["stage"] == "written"
    assert result["state"] == ("failed" if remove_transaction else "passed")
    assert store.statement(SOURCE)["review"]["approval"] == approval
    assert ledger.read_bytes() == ledger_before
    if not remove_transaction:
        assert (store.root / PARSED).read_bytes() == completed_bytes


def test_reopened_changed_decisions_can_receive_review_checks(
    review_store: ReviewFiles,
) -> None:
    store = review_store
    complete(store)
    (store.root / "ledger.beancount").write_text(BASE + ledger_transaction(store))
    assert validate(store)["state"] == "passed"
    doc = store.statement(SOURCE)
    doc["extracted_records"][0]["description"] = "Corrected source description"
    save(store, PARSED, doc)
    set_status(store, "done")
    assert validate(store, "review")["state"] == "failed"
    set_status(store, "final_review")  # Explicitly reopened for review.
    report = validate(store, "review")
    assert report["stage"] == "review"
    assert report["state"] == "passed"
    assert validate(store, "written")["state"] == "failed"


@pytest.mark.parametrize("remove_price", [False, True])
def test_statement_review_rechecks_written_redundant_prices(
    review_store: ReviewFiles, remove_price: bool
) -> None:
    store = review_store
    complete(store)
    directive = "2026-01-30 price STOCK 20 EUR"
    ledger = store.root / "ledger.beancount"
    ledger.write_text(BASE + "\n" + directive + "\n")
    session = store.read(store.session_path)
    session["price_runs"] = [
        {
            "run_id": "redundant",
            "detail": "Provider confirmed the existing quote",
            "requested_date": "2026-01-31",
            "state": "complete",
            "required_commodities": ["STOCK"],
            "coverage": ["STOCK"],
            "preflight": "passed",
            "preflight_job_count": 1,
            "jobs": [
                {
                    "commodity": "STOCK",
                    "source": "fixture",
                    "requested_date": "2026-01-31",
                    "quote_date": "2026-01-30",
                    "outcome": "redundant",
                    "directive": directive,
                }
            ],
            "execution": {
                "state": "complete",
                "exit_code": 0,
                "duration_seconds": 0.1,
                "stderr_summary": "",
            },
        }
    ]
    save(store, store.session_path, session)
    result = reconciliation.validate_import(store.root, store.session_id, "written")
    assert result["prices"].get("redundant", {}).get("state") == "passed", result
    before = (store.root / store.session_path).read_bytes()
    if remove_price:
        ledger.write_text(BASE)
    result = reconciliation.validate_import(store.root, store.session_id, "review")
    price = result["prices"]["redundant"]
    assert price["stage"] == "written"
    assert price["state"] == ("failed" if remove_price else "passed")
    if not remove_price:
        assert (store.root / store.session_path).read_bytes() == before


@pytest.mark.parametrize("stage", [None, "approved", "complete"])
def test_validation_report_requires_a_declared_stage(
    review_store: ReviewFiles,
    stage: str | None,
) -> None:
    store = review_store
    complete(store)
    validate(store, "review")
    doc = store.statement(SOURCE)
    if stage is None:
        del doc["review"]["validation"]["stage"]
    else:
        doc["review"]["validation"]["stage"] = stage
    with pytest.raises(WorkflowError, match="Schema violation"):
        validate_state("parsed", store.root, doc)


def test_no_session_validation_leaves_historical_artifacts_alone(
    review_store: ReviewFiles,
) -> None:
    store = review_store
    set_status(store, "done")
    # A workspace validation does not require rewriting completed import artifacts.
    for path in (store.root / PARSED, store.root / store.session_path):
        path.write_text("Historical artifact with no current schema\n")
    report = reconciliation.validate_import(store.root)
    assert report["state"] == "passed", report
    assert report["statements"] == report["prices"] == {}
    assert (
        store.root / PARSED
    ).read_text() == "Historical artifact with no current schema\n"
    assert (
        reconciliation.validate_import(store.root, store.session_id)["state"]
        == "failed"
    )


def test_validation_cli_reports_changed_artifacts_and_noop_recheck(
    review_store: ReviewFiles,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = review_store
    complete(store)
    monkeypatch.setattr(
        "sys.argv",
        [
            "validate",
            "--workspace",
            str(store.root),
            "--session",
            store.session_id,
            "--stage",
            "review",
        ],
    )
    assert reconciliation.main() == 0
    result = json.loads(capsys.readouterr().out)
    assert PARSED in result["changed_files"]
    assert result["changed_files"] == sorted(result["file_sha256"])
    for path in result["changed_files"]:
        assert result["file_sha256"][path] == digest((store.root / path).read_bytes())
    assert reconciliation.main() == 0
    assert json.loads(capsys.readouterr().out)["changed_files"] == []


def test_invalid_validation_stage_does_not_edit_artifacts(
    review_store: ReviewFiles,
) -> None:
    store = review_store
    complete(store)
    before = (store.root / PARSED).read_bytes()
    report = reconciliation.validate_import(store.root, store.session_id, "approved")
    assert report["state"] == "failed"
    assert "stage" in report["errors"][0]
    assert (store.root / PARSED).read_bytes() == before


@pytest.mark.parametrize("target", ["parsed", "source", "ledger"])
def test_validation_detects_direct_edits_during_check(
    review_store: ReviewFiles, monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    store = review_store
    complete(store)
    inspect = reconciliation._inspect_statement

    def concurrent_edit(
        files: ReviewFiles, source: str, stage: str = "written"
    ) -> dict[str, Any]:
        result = inspect(files, source, stage)
        if target == "parsed":
            doc = files.statement(SOURCE)
            doc["extracted_records"][0]["description"] = "User correction"
            save(files, PARSED, doc)
        elif target == "source":
            (files.root / SOURCE).write_text("Changed source evidence\n")
        else:
            with (files.root / "ledger.beancount").open("a") as stream:
                stream.write("\n; concurrent user edit\n")
        return result

    monkeypatch.setattr(reconciliation, "_inspect_statement", concurrent_edit)
    report = reconciliation.validate_import(store.root, store.session_id, "review")
    assert report["state"] == "failed"
    assert any("changed" in error.lower() for error in report["errors"])
    if target == "parsed":
        assert (
            store.statement(SOURCE)["extracted_records"][0]["description"]
            == "User correction"
        )


def test_incomplete_cost_is_a_validation_error_not_a_crash(
    review_store: ReviewFiles,
) -> None:
    doc = complete(review_store)
    doc["extracted_records"][0]["review"]["postings"][1]["cost"] = "{EUR}"
    save(review_store, PARSED, doc)
    report = reconciliation.validate_import(
        review_store.root, review_store.session_id, "review"
    )
    assert report["state"] == "failed"
    assert any("explicit" in error for error in report["errors"])


@pytest.mark.parametrize(
    "constraint", ["missing", "future", "closed", "currency", "proposed"]
)
def test_review_checks_posting_account_constraints_before_writes(
    review_store: ReviewFiles, constraint: str
) -> None:
    store = review_store
    doc = complete(store)
    doc["extracted_records"][0]["review"]["postings"][1]["account"] = "Expenses:New"
    directive = {
        "missing": "",
        "future": "2026-02-01 open Expenses:New EUR\n",
        "closed": "2025-01-01 open Expenses:New EUR\n2025-12-01 close Expenses:New\n",
        "currency": "2025-01-01 open Expenses:New USD\n",
        "proposed": "",
    }[constraint]
    if constraint == "proposed":
        doc["statement_metadata"]["accounts"][0]["review"]["proposed_directives"] = [
            "2026-01-02 open Expenses:New EUR"
        ]
    save(store, PARSED, doc)
    (store.root / "ledger.beancount").write_text(BASE + directive)
    before = (store.root / "ledger.beancount").read_bytes()
    result = reconciliation.validate_import(store.root, store.session_id, "review")
    assert result["state"] == ("passed" if constraint == "proposed" else "failed"), (
        result
    )
    assert (store.root / "ledger.beancount").read_bytes() == before


@pytest.mark.parametrize("other_units", ["", "24 EUR"])
def test_review_rejects_incomplete_or_unbalanced_supporting_transaction(
    review_store: ReviewFiles, other_units: str
) -> None:
    doc = complete(review_store)
    doc["statement_metadata"]["accounts"][0]["review"]["proposed_directives"] = [
        '2026-01-01 * "Opening"\n  Assets:Checking -25 EUR\n  Expenses:Food '
        + other_units
    ]
    save(review_store, PARSED, doc)
    result = reconciliation.validate_import(
        review_store.root, review_store.session_id, "review"
    )
    assert result["state"] == "failed"
    assert result["errors"]


def add_group_member(store: ReviewFiles, *, complete_member: bool = True) -> str:
    peer_source = "statements/raw/peer.csv"
    doc = copy.deepcopy(store.statement(SOURCE))
    (store.root / peer_source).write_text("peer source")
    doc["source_file"] = peer_source
    doc["source_fingerprint"] = "sha256:" + digest(
        (store.root / peer_source).read_bytes()
    )
    if not complete_member:
        doc["extraction_state"] = "pending"
        doc["statement_metadata"] = {"accounts": []}
        doc["extracted_records"] = []
        doc["review"] = {
            "processing": {
                "attempts": 0,
                "outcome": "pending",
                "warnings": [],
                "evidence": [],
            }
        }
    session = store.read(store.session_path)
    session["groups"][0]["source_files"].append(peer_source)
    save(store, store.session_path, session)
    status_path = store.root / "statements/import-status.yml"
    status = yaml.safe_load(status_path.read_text())
    status["groups"]["review"]["sources"][peer_source] = {
        "source_fingerprint": doc["source_fingerprint"]
    }
    status_path.write_text(yaml.safe_dump(status))
    save(store, PARSED, doc)
    return peer_source


def test_group_edits_preserve_sibling_source_sections(
    review_store: ReviewFiles,
) -> None:
    store = review_store
    doc = complete(store)
    before_paths = set((store.root / "statements/parsed").glob("*.json"))
    peer = add_group_member(store)
    sibling = copy.deepcopy(store.statement(peer))
    store.submit(
        SOURCE,
        {
            "kind": "mapping",
            "subject_id": "checking",
            "value": "Assets:Checking",
            "expected_etag": etag(doc),
        },
    )
    assert store.statement(peer) == sibling
    assert (
        account_decisions(store.statement(SOURCE))["checking"]["state"] == "needs_input"
    )
    assert set((store.root / "statements/parsed").glob("*.json")) == before_paths
    assert len(store.read(PARSED)["statements"]) == 2


def test_partial_group_cannot_pass_completion(review_store: ReviewFiles) -> None:
    store = review_store
    complete(store)
    peer = add_group_member(store, complete_member=False)
    (store.root / "ledger.beancount").write_text(BASE + ledger_transaction(store))
    set_status(store, "final_review")
    result = reconciliation.validate_import(store.root, store.session_id, "written")
    assert result["statements"][SOURCE]["state"] == "passed"
    assert result["statements"][peer]["state"] == "failed"
    assert result["groups"]["review"]["state"] == "failed"
    set_status(store, "done")
    result = reconciliation.validate_import(store.root, store.session_id, "written")
    assert result["state"] == "failed"
    assert any(
        "done requires written validation" in error for error in result["errors"]
    )


@pytest.mark.parametrize(
    "defect", ["missing_member", "extra_member", "wrong_group", "fingerprint"]
)
def test_group_file_must_match_session_and_status(
    review_store: ReviewFiles, defect: str
) -> None:
    store = review_store
    complete(store)
    peer = add_group_member(store)
    group = store.read(PARSED)
    if defect == "missing_member":
        group["statements"] = [group["statements"][0]]
    elif defect == "extra_member":
        extra = copy.deepcopy(group["statements"][0])
        extra["source_file"] = "statements/raw/extra.csv"
        group["statements"].append(extra)
    elif defect == "wrong_group":
        group["group_id"] = "other"
    else:
        group["statements"][1]["source_fingerprint"] = "sha256:" + "0" * 64
    save(store, PARSED, group)
    with pytest.raises(WorkflowError):
        store.statement(peer)


def test_batch_saves_are_durable_and_gate_all_required_inputs(
    review_store: ReviewFiles,
) -> None:
    store = review_store
    doc = complete(store)
    doc["review"]["processing"]["needs_input"] = True
    doc["statement_metadata"]["accounts"][0]["review"]["state"] = "needs_input"
    doc["extracted_records"][0]["review"]["state"] = "needs_input"
    save(store, PARSED, doc)
    assert len(store.review_batch()["blockers"]) == 3
    for kind, subject, value in [
        ("statement", "statement", "Use the unlocked source"),
        ("account", "checking", "This is my checking account"),
        ("transaction", "row-1", "Groceries"),
    ]:
        store.submit(
            SOURCE,
            {
                "kind": "answer",
                "subject_kind": kind,
                "subject_id": subject,
                "value": value,
                "expected_etag": etag(store.statement(SOURCE)),
            },
        )
    reopened = ReviewFiles(store.root, store.session_id)
    batch = reopened.review_batch()
    assert batch["ready"] and batch["pending_count"] == 3
    assert (
        reopened.statement(SOURCE)["extracted_records"][0]["review"]["answer"]
        == "Groceries"
    )
    assert (
        reopened.statement(SOURCE)["extracted_records"][0]["review"]["state"]
        == "needs_input"
    )
    assert reopened.prepare_batch(batch["token"])["subjects"] == [SOURCE]
    reopened.acknowledge_batch(batch["pending_token"])
    assert reopened.review_batch()["pending_count"] == 0
    assert reopened.review_batch()["blockers"] == []


def test_batch_rechecks_changed_questions_and_does_not_clear_new_saves(
    review_store: ReviewFiles,
) -> None:
    store = review_store
    complete(store)

    def respond(value: str) -> None:
        store.submit(
            SOURCE,
            {
                "kind": "answer",
                "subject_kind": "transaction",
                "subject_id": "row-1",
                "value": value,
                "expected_etag": etag(store.statement(SOURCE)),
            },
        )

    respond("Groceries")
    first = store.review_batch()
    doc = store.statement(SOURCE)
    doc["extracted_records"][0]["review"]["rationale"] = (
        "New evidence: please review again"
    )
    save(store, PARSED, doc)
    assert not store.review_batch()["ready"]
    with pytest.raises(WorkflowError, match="changed or remain unanswered"):
        store.prepare_batch(first["token"])
    respond("Confirmed with new evidence")
    store.acknowledge_batch(first["pending_token"])
    assert store.review_batch()["pending_count"] == 1


def test_batch_requires_current_final_review_approval(
    review_store: ReviewFiles,
) -> None:
    store = review_store
    complete(store)
    final_review(store)
    assert any("approval" in b for b in store.review_batch()["blockers"])
    approve(store)
    assert store.review_batch()["ready"]
    # Editing a previously approved row reopens its decision and invalidates approval.
    doc = store.statement(SOURCE)
    store.submit(
        SOURCE,
        {
            "kind": "postings",
            "subject_id": "row-1",
            "value": doc["extracted_records"][0]["review"]["postings"],
            "expected_etag": etag(doc),
        },
    )
    assert store.review_batch()["ready"]
    assert "approval" not in store.statement(SOURCE)["review"]


def test_batch_does_not_require_unavailable_raw_stage_inputs(
    review_store: ReviewFiles,
) -> None:
    store = review_store
    status = yaml.safe_load((store.root / "statements/import-status.yml").read_text())
    status["groups"]["review"]["current_status"] = "raw_ready"
    (store.root / "statements/import-status.yml").write_text(yaml.safe_dump(status))
    (store.root / PARSED).unlink(missing_ok=True)
    assert store.review_batch()["blockers"] == []
