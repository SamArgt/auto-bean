"""Read-only validation of versioned workflow state; no accounting decisions."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, NoReturn

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from auto_bean.common import PLUGIN, WorkflowError, checked_path


def invalid(message: str) -> NoReturn:
    raise WorkflowError("invalid_state", message)


def unique_mapping(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            invalid("Duplicate mapping key; repair the owning state file.")
        result[key] = value
    return result


class StateLoader(yaml.SafeLoader):
    pass


def yaml_mapping(loader: StateLoader, node: yaml.MappingNode) -> dict[str, Any]:
    loader.flatten_mapping(node)
    pairs = []
    for key, value in node.value:
        name = loader.construct_object(key)
        if not isinstance(name, str):
            invalid("State mapping keys must be strings.")
        pairs.append((name, loader.construct_object(value)))
    return unique_mapping(pairs)


StateLoader.add_constructor("tag:yaml.org,2002:map", yaml_mapping)


def yaml_timestamp(loader: StateLoader, node: yaml.ScalarNode) -> str:
    return loader.construct_scalar(node)


StateLoader.add_constructor("tag:yaml.org,2002:timestamp", yaml_timestamp)

FORMATS = FormatChecker()


@FORMATS.checks("date-time", raises=ValueError)
def timestamp(value: object) -> bool:
    if not isinstance(value, str):
        return True  # Type constraints belong to the schema.
    value = value.upper()
    if not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})",
        value,
    ):
        return False
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.tzinfo is not None


def load_state(path: Path) -> dict[str, Any]:
    try:
        value = (
            yaml.load(path.read_text(), Loader=StateLoader)
            if path.suffix in {".yml", ".yaml"}
            else json.loads(path.read_text(), object_pairs_hook=unique_mapping)
        )
    except (yaml.YAMLError, ValueError):
        invalid(f"Cannot parse {path.name}; repair syntax without discarding data.")
    if not isinstance(value, dict):
        invalid("Expected a state object.")
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError):
        invalid("State contains a non-JSON value or non-finite number.")
    return dict(value)


def bounded_path(root: Path, value: str, prefix: str) -> Path:
    path = checked_path(root, value)
    if not path.is_relative_to(root / prefix) or path == root / prefix:
        invalid(f"State path must stay under {prefix}.")
    return path


def unique_ids(records: list[dict[str, Any]], field: str) -> None:
    values = [record[field] for record in records if field in record]
    if len(values) != len(set(values)):
        invalid(f"Duplicate {field} values.")


def validate_parsed(root: Path, data: dict[str, Any]) -> None:
    bounded_path(root, data["source_file"], "statements/raw")
    if data.get("schema_version", 1) == 1:
        bounded_path(root, data["process_artifact"], ".auto-bean/artifacts/process")
    metadata = data["statement_metadata"]
    accounts = metadata["accounts"]
    records = data["extracted_records"]
    unique_ids(accounts, "account_id")
    unique_ids(records, "record_id")
    ids = {account["account_id"] for account in accounts}
    if any(record["account_id"] not in ids for record in records):
        invalid("Record account_id does not reference a parsed account.")
    period = metadata.get("statement_period")
    if period and period["start_date"] > period["end_date"]:
        invalid("Statement period ends before it starts.")
    if data.get("schema_version") == 2:
        validate_review(root, data, ids, {r["record_id"] for r in records})


def validate_review(
    root: Path, data: dict[str, Any], accounts: set[str], records: set[str]
) -> None:
    from auto_bean.review import account_decisions, transaction_decisions

    review = data["review"]
    for block in [
        review["processing"],
        *account_decisions(data).values(),
        *transaction_decisions(data).values(),
    ]:
        if "answer" in block and not block["answer"].strip():
            invalid("Answers require nonempty text.")
    for decision in transaction_decisions(data).values():
        if decision["disposition"] == "existing_duplicate":
            reference = decision.get("existing_transaction")
            if reference is None:
                invalid(
                    "Existing duplicates require a canonical transaction reference."
                )
            path = checked_path(root, reference["path"])
            if reference["path"] != "ledger.beancount" and (
                not path.is_relative_to(root / "beancount")
                or path.suffix != ".beancount"
            ):
                invalid(
                    "Existing transaction references must use canonical ledger paths."
                )
        if decision["disposition"] == "paired_transfer" and (
            not decision.get("posting_owner") or not decision.get("linked_records")
        ):
            invalid("Paired transfer requires links and a single posting owner.")
        for link in decision.get("linked_records", []):
            bounded_path(root, link["source_file"], "statements/raw")
            if link["source_file"] == data["source_file"] and not any(
                row["account_id"] == link["account_id"]
                and row["record_id"] == link["record_id"]
                for row in data["extracted_records"]
            ):
                invalid("Linked record does not exist.")


def validate_session(root: Path, data: dict[str, Any]) -> None:
    unique_ids(data["statements"], "source_file")
    unique_ids(data["statements"], "parsed_statement")
    unique_ids(data["price_runs"], "run_id")
    for statement in data["statements"]:
        bounded_path(root, statement["source_file"], "statements/raw")
        bounded_path(root, statement["parsed_statement"], "statements/parsed")
    for run in data["price_runs"]:
        if run["state"] in {"complete", "no_op", "failed", "partial"} and run[
            "execution"
        ]["state"] not in {"complete", "timed_out"}:
            invalid("A terminal price outcome cannot refer to a running execution.")
        if (
            run["state"] in {"complete", "no_op", "failed", "partial"}
            and run["preflight"] == "passed"
            and run["preflight_job_count"] != len(run["jobs"])
        ):
            invalid(
                "Terminal price outcomes must account for every preflight job, including unaccounted jobs."
            )
        if any(
            job["outcome"] in {"emitted", "redundant"} and not job.get("quote_date")
            for job in run["jobs"]
        ):
            invalid("Emitted or redundant price jobs require the actual quote date.")
        if run["state"] == "no_op" and (run["jobs"] or run["required_commodities"]):
            invalid("Zero-job price result has required work.")
        if run["state"] in {"complete", "no_op"} and (
            run["execution"]["state"] != "complete"
            or run["execution"]["exit_code"] != 0
            or run["preflight"] != "passed"
            or run["preflight_job_count"] != len(run["jobs"])
        ):
            invalid(
                "Price completion lacks a successful terminal run or reconciled job count."
            )
        if run["state"] == "complete" and any(
            j["outcome"] in {"failed", "unaccounted"} for j in run["jobs"]
        ):
            invalid("Price completion has unresolved jobs.")
        if run["state"] == "complete" and (
            run["preflight"] != "passed"
            or set(run["required_commodities"]) - set(run["coverage"])
            or set(run["required_commodities"])
            - {job["commodity"] for job in run["jobs"]}
        ):
            invalid("Price completion lacks preflight or required commodity coverage.")


def validate_status(root: Path, data: dict[str, Any]) -> None:
    pointers: set[str] = set()
    sources: set[Path] = set()
    for raw, entry in data["statements"].items():
        source = bounded_path(root, raw, "statements/raw")
        if source in sources:
            invalid("Multiple status entries point to the same raw source.")
        sources.add(source)
        if entry.get("source_path", raw) != raw:
            invalid("Status source_path disagrees with its entry key.")
        paths = []
        if "parsed_statement" in entry:
            paths.append((entry["parsed_statement"], "statements/parsed"))
        paths.extend(
            (value, f".auto-bean/artifacts/{stage}")
            for stage, value in entry.get("artifacts", {}).items()
        )
        for value, prefix in paths:
            path = bounded_path(root, value, prefix)
            canonical = path.as_posix()
            if canonical in pointers:
                invalid("Statements have conflicting parsed or artifact pointers.")
            pointers.add(canonical)


def validate_memory(root: Path, data: dict[str, Any]) -> None:
    if data["memory_type"] == "import_source_behavior_index":
        sources = data["sources"]
        paths: set[Path] = set()
        unique_ids(sources, "source_slug")
        unique_ids(sources, "path")
        for source in sources:
            if Path(source["path"]).is_absolute():
                invalid("Import-source index paths must be relative.")
            path = bounded_path(
                root,
                ".auto-bean/memory/import_sources/" + source["path"],
                ".auto-bean/memory/import_sources",
            )
            if path in paths:
                invalid("Multiple index entries point to the same source file.")
            paths.add(path)
        return
    records = data["records"]
    unique_ids(records, "record_id")
    if any(record["memory_type"] != data["memory_type"] for record in records):
        invalid("Memory record type disagrees with its containing file.")


def validate_state(kind: str, root: Path, data: dict[str, Any]) -> None:
    schema_kind = (
        "parsed-v2" if kind == "parsed" and data.get("schema_version") == 2 else kind
    )
    schema = json.loads(
        (PLUGIN / f"references/schemas/{schema_kind}.schema.json").read_text()
    )
    validator = Draft202012Validator(schema, format_checker=FORMATS)
    error = next(validator.iter_errors(data), None)
    if error is not None:
        location = ".".join(str(part) for part in error.absolute_path) or "root"
        invalid(f"Schema violation at {location} ({error.validator}).")
    {
        "parsed": validate_parsed,
        "status": validate_status,
        "memory": validate_memory,
        "session": validate_session,
    }[kind](root, data)
