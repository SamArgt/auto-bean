from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from auto_bean.common import PLUGIN, WorkflowError
from auto_bean.validation import load_state, validate_state


@pytest.fixture
def parsed() -> dict[str, Any]:
    return dict(
        json.loads(
            (Path(__file__).parent / "fixtures/parsed-statement-v1.json").read_text()
        )
    )


def index(status: str, *, fingerprint: str = "a" * 64) -> dict[str, Any]:
    return {
        "version": 1,
        "groups": {
            "checking": {
                "session_id": "test",
                "current_status": status,
                "parsed_group": "statements/parsed/checking.json",
                "sources": {
                    "statements/raw/checking.csv": {
                        "source_fingerprint": "sha256:" + fingerprint
                    }
                },
            }
        },
    }


def test_packaged_schemas_are_valid_and_template_memory_remains_readable(
    current: Path,
) -> None:
    for path in (PLUGIN / "references/schemas").glob("*.json"):
        Draft202012Validator.check_schema(json.loads(path.read_text()))
    for path in (current / ".auto-bean/memory").rglob("*.json"):
        validate_state("memory", current, load_state(path))
    validate_state(
        "status", current, load_state(current / "statements/import-status.yml")
    )


def test_multi_account_evidence_is_valid(current: Path, parsed: dict[str, Any]) -> None:
    other = {"account_id": "savings", "primary_currency": "EUR"}
    parsed["statement_metadata"]["accounts"].append(other)
    parsed["extracted_records"][1]["account_id"] = "savings"
    validate_state("parsed", current, parsed)


@pytest.mark.parametrize(
    "failure",
    [
        "duplicate_account",
        "duplicate_record",
        "missing_account",
        "float_amount",
        "invalid_date",
        "invalid_timestamp",
        "period_order",
        "escaping_source",
        "escaping_artifact",
        "unknown_version",
    ],
)
def test_invalid_parsed_evidence_is_rejected(
    current: Path, parsed: dict[str, Any], failure: str
) -> None:
    records = parsed["extracted_records"]
    if failure == "duplicate_account":
        parsed["statement_metadata"]["accounts"] *= 2
    elif failure == "duplicate_record":
        records[1]["record_id"] = records[0]["record_id"]
    elif failure == "missing_account":
        records[0]["account_id"] = "unknown"
    elif failure == "float_amount":
        records[0]["amount"] = -4.5
    elif failure == "invalid_date":
        records[0]["transaction_date"] = "2026-02-30"
    elif failure == "invalid_timestamp":
        parsed["parsed_at"] = "yesterday"
    elif failure == "period_order":
        parsed["statement_metadata"]["statement_period"]["start_date"] = "2026-02-01"
    elif failure == "escaping_source":
        parsed["source_file"] = "statements/raw/../../private.csv"
    elif failure == "escaping_artifact":
        parsed["process_artifact"] = "/tmp/private.md"
    else:
        parsed["schema_version"] = 99
    with pytest.raises(WorkflowError):
        validate_state("parsed", current, parsed)


def test_transaction_export_does_not_invent_statement_balances(
    current: Path, parsed: dict[str, Any]
) -> None:
    parsed["document_kind"] = "transaction_export"
    del parsed["statement_metadata"]["statement_period"]
    for account in parsed["statement_metadata"]["accounts"]:
        account.pop("opening_balance", None)
        account.pop("closing_balance", None)
    validate_state("parsed", current, parsed)


@pytest.mark.parametrize(
    "content,suffix",
    [
        ('{"records": [], "records": [1]}', ".json"),
        ("version: 1\nversion: 2\n", ".yml"),
        (
            "statements:\n  source:\n    current_status: done\n    current_status: raw_ready\n",
            ".yml",
        ),
    ],
)
def test_duplicate_keys_fail_without_silent_data_loss(
    tmp_path: Path, content: str, suffix: str
) -> None:
    path = tmp_path / ("state" + suffix)
    path.write_text(content)
    with pytest.raises(WorkflowError, match="Duplicate"):
        load_state(path)
    assert path.read_text() == content


def test_status_dates_and_pointers_are_checked(current: Path) -> None:
    data = index("raw_ready")
    entry = data["groups"]["checking"]
    entry["updated_at"] = "2026-10-19T10:00:00Z"
    validate_state("status", current, data)
    data["groups"]["savings"] = copy.deepcopy(entry)
    with pytest.raises(WorkflowError, match="conflicting"):
        validate_state("status", current, data)


def test_legacy_memory_ids_are_readable_but_duplicates_are_rejected(
    current: Path,
) -> None:
    path = PLUGIN / "skills/auto-bean-memory/references/memory-examples.md"
    examples = [
        json.loads(block)
        for block in re.findall(r"```json\n(.*?)```", path.read_text(), re.DOTALL)
    ]
    record = next(
        example for example in examples if example["memory_type"] == "category_mapping"
    )
    data: dict[str, Any] = {
        "schema_version": 1,
        "memory_type": "category_mapping",
        "records": [record],
    }
    validate_state("memory", current, data)
    data["records"].append(copy.deepcopy(record))
    with pytest.raises(WorkflowError, match="record_id"):
        validate_state("memory", current, data)
    data["records"].pop()
    del record["record_id"]
    validate_state("memory", current, data)


def test_source_index_cannot_escape_or_follow_symlinks(
    current: Path, tmp_path: Path
) -> None:
    data: dict[str, Any] = {
        "schema_version": 1,
        "memory_type": "import_source_behavior_index",
        "sources": [{"source_slug": "bank", "path": "../private.json"}],
    }
    with pytest.raises(WorkflowError):
        validate_state("memory", current, data)
    directory = current / ".auto-bean/memory/import_sources"
    (directory / "bank.json").symlink_to(tmp_path / "outside.json")
    data["sources"][0]["path"] = "bank.json"
    with pytest.raises(WorkflowError, match="symlink"):
        validate_state("memory", current, data)


@pytest.mark.parametrize(
    "content,suffix", [('{"confidence": NaN}', ".json"), ("confidence: .inf\n", ".yml")]
)
def test_non_finite_state_is_rejected(
    tmp_path: Path, content: str, suffix: str
) -> None:
    path = tmp_path / ("state" + suffix)
    path.write_text(content)
    with pytest.raises(WorkflowError, match="non-finite"):
        load_state(path)


def test_raw_source_aliases_are_not_two_statements(current: Path) -> None:
    data = index("raw_ready")
    data["groups"]["checking"]["sources"]["./statements/raw/checking.csv"] = {
        "source_fingerprint": "sha256:" + "a" * 64
    }
    with pytest.raises(WorkflowError, match="same raw source"):
        validate_state("status", current, data)


@pytest.mark.parametrize("grouped", [False, True])
def test_session_groups_partition_statements(current: Path, grouped: bool) -> None:
    data = load_state(PLUGIN / "references/import-session.example.json")
    data["price_runs"] = []
    peer = "statements/raw/savings.csv"
    if grouped:
        data["groups"][0]["source_files"].append(peer)
        data["groups"][0]["origin"] = "user"
    else:
        data["groups"].append(
            {
                "group_id": "savings",
                "parsed_group": "statements/parsed/savings.json",
                "name": "Savings",
                "origin": "agent",
                "source_files": [peer],
            }
        )
    validate_state("session", current, data)


@pytest.mark.parametrize(
    "defect",
    [
        "missing_groups",
        "missing_path",
        "escaping_member",
        "overlap",
        "duplicate_id",
        "empty_group",
        "duplicate_member",
        "blank_name",
    ],
)
def test_invalid_session_groups_are_rejected(current: Path, defect: str) -> None:
    data = load_state(PLUGIN / "references/import-session.example.json")
    data["price_runs"] = []
    group = data["groups"][0]
    if defect == "missing_groups":
        del data["groups"]
    elif defect == "missing_path":
        del group["parsed_group"]
    elif defect == "escaping_member":
        group["source_files"] = ["../unknown.csv"]
    elif defect in {"overlap", "duplicate_id"}:
        other = copy.deepcopy(group)
        if defect == "overlap":
            other["group_id"] = "other"
        data["groups"].append(other)
    elif defect == "empty_group":
        group["source_files"] = []
    elif defect == "duplicate_member":
        group["source_files"] *= 2
    elif defect == "blank_name":
        group["name"] = "   "
    with pytest.raises(WorkflowError):
        validate_state("session", current, data)


def test_empty_session_has_no_groups(current: Path) -> None:
    data = load_state(PLUGIN / "references/import-session.example.json")
    data.update(groups=[], price_runs=[])
    validate_state("session", current, data)


def test_group_examples_agree_on_identity_and_membership(current: Path) -> None:
    from auto_bean.validation import session_status

    session = load_state(PLUGIN / "references/import-session.example.json")
    status = load_state(PLUGIN / "references/import-status.example.yml")
    parsed = load_state(PLUGIN / "references/parsed-statement-output.example.json")
    validate_state("session", current, session)
    validate_state("status", current, status)
    validate_state("parsed-group", current, parsed)
    session_status(session, status)
    group = session["groups"][0]
    assert group["group_id"] == parsed["group_id"]
    assert set(group["source_files"]) == {
        s["source_file"] for s in parsed["statements"]
    }


def test_source_cannot_carry_a_lifecycle_status(current: Path) -> None:
    data = index("raw_ready")
    data["groups"]["checking"]["sources"]["statements/raw/checking.csv"][
        "current_status"
    ] = "done"
    with pytest.raises(WorkflowError):
        validate_state("status", current, data)
