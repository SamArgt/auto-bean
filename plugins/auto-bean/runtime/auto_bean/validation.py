"""Read-only validation of versioned workflow state; no accounting decisions."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, NoReturn

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from auto_bean.common import PLUGIN, WorkflowError, checked_path, workspace

TRANSITIONS: dict[str, set[str]] = {
    "raw_ready": {"process_blocked", "process_review", "account_review"},
    "process_blocked": {"raw_ready", "process_review", "account_review"},
    "process_review": {"process_blocked", "account_review"},
    "account_review": {"account_blocked", "balance_review"},
    "account_blocked": {"balance_review"},
    "balance_review": {"balance_blocked", "categorize_ready"},
    "balance_blocked": {"categorize_ready"},
    "categorize_ready": {"categorize_blocked", "categorize_review"},
    "categorize_blocked": {"categorize_review"},
    "categorize_review": {"categorize_blocked", "write_ready"},
    "write_ready": {"write_blocked", "final_review"},
    "write_blocked": {"final_review", "categorize_blocked"},
    "final_review": {"done", "write_blocked", "categorize_blocked"},
    "done": set(),
}


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


def validate_transitions(
    previous: dict[str, Any],
    current: dict[str, Any],
    *,
    approved: set[str] | None = None,
    rework: set[str] | None = None,
) -> None:
    approved, rework = approved or set(), rework or set()
    before = previous["statements"]
    after = current["statements"]
    if before.keys() - after.keys():
        invalid("Status update removed existing statement entries.")
    for raw, entry in after.items():
        new = entry["current_status"]
        if raw not in before:
            if new != "raw_ready":
                invalid("New statements must start at raw_ready.")
            continue
        old = before[raw]["current_status"]
        changed_source = (
            entry["source_fingerprint"] != before[raw]["source_fingerprint"]
        )
        if raw in rework and new == "raw_ready":
            continue
        if changed_source:
            if old == "done" or new != "raw_ready":
                invalid(
                    "Changed sources must restart; completed sources need explicit rework."
                )
            continue
        if old == "done" and entry != before[raw]:
            invalid(
                "Completed statement state requires explicit rework before changes."
            )
        if new == "raw_ready" and old != "raw_ready":
            invalid("Restarting extraction requires explicit rework.")
        if new != old and new not in TRANSITIONS[old]:
            invalid(f"Illegal status transition: {old} -> {new}.")
        if new == "done" and old != "done" and raw not in approved:
            invalid("Final review requires explicit approval before done.")
        if new == "done" and (
            entry.get("user_input_required") or entry.get("manual_resolution_required")
        ):
            invalid("Unresolved input or manual repair prevents completion.")
        if entry.get("process_attempts", 0) < before[raw].get("process_attempts", 0):
            invalid(
                "Retry count decreased without a changed source or explicit rework."
            )


def validate_state(kind: str, root: Path, data: dict[str, Any]) -> None:
    schema = json.loads((PLUGIN / f"references/schemas/{kind}.schema.json").read_text())
    validator = Draft202012Validator(schema, format_checker=FORMATS)
    error = next(validator.iter_errors(data), None)
    if error is not None:
        location = ".".join(str(part) for part in error.absolute_path) or "root"
        invalid(f"Schema violation at {location} ({error.validator}).")
    {"parsed": validate_parsed, "status": validate_status, "memory": validate_memory}[
        kind
    ](root, data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("parsed", "status", "memory"))
    parser.add_argument("path")
    parser.add_argument("--previous")
    parser.add_argument("--approved", action="append", default=[])
    parser.add_argument("--rework", action="append", default=[])
    args = parser.parse_args()
    try:
        root = workspace(Path.cwd())
        path = checked_path(root, args.path)
        data = load_state(path)
        validate_state(args.kind, root, data)
        if args.previous:
            if args.kind != "status":
                invalid("Previous snapshots are supported only for status updates.")
            previous = load_state(checked_path(root, args.previous))
            validate_state("status", root, previous)
            validate_transitions(
                previous, data, approved=set(args.approved), rework=set(args.rework)
            )
        elif args.approved or args.rework:
            invalid("Approval/rework checks require a previous status snapshot.")
    except (WorkflowError, OSError) as error:
        print(json.dumps({"status": "failed", "message": str(error)}))
        return 1
    print(json.dumps({"status": "ok", "kind": args.kind, "path": args.path}))
    return 0
