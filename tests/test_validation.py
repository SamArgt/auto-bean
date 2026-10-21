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
        "statements": {
            "statements/raw/checking.csv": {
                "current_status": status,
                "source_fingerprint": "sha256:" + fingerprint,
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
    entry = next(iter(data["statements"].values()))
    entry["updated_at"] = "2026-10-19T10:00:00Z"
    path = current / "status.yml"
    path.write_text(
        "version: 1\nstatements:\n  statements/raw/checking.csv:\n    current_status: raw_ready\n    source_fingerprint: sha256:"
        + "a" * 64
        + "\n    updated_at: 2026-10-19T10:00:00Z\n"
    )
    validate_state("status", current, load_state(path))
    entry["parsed_statement"] = "statements/parsed/same.json"
    data["statements"]["statements/raw/savings.csv"] = copy.deepcopy(entry)
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
    data["statements"]["./statements/raw/checking.csv"] = copy.deepcopy(
        next(iter(data["statements"].values()))
    )
    with pytest.raises(WorkflowError, match="same raw source"):
        validate_state("status", current, data)
