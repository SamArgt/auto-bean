from __future__ import annotations

import difflib

import yaml

from auto_bean.validation import load_state, validate_state, bounded_path
from pathlib import Path
from typing import Any

from auto_bean.common import (
    FORMAT_VERSION,
    PLUGIN,
    STATE,
    TEMPLATE,
    WorkflowError,
    atomic_write,
    checked_path,
    digest,
    ignore_contents,
    json_bytes,
    read_json,
    workspace,
)
from auto_bean.runtime import ensure_runtime, validate

LEGACY_SKILLS = (
    "auto-bean-query",
    "auto-bean-write",
    "auto-bean-import",
    "auto-bean-process",
    "auto-bean-categorize",
    "auto-bean-memory",
    "auto-bean-prices",
    "shared",
)
LEGACY_SCRIPTS = ("install-dependencies.sh", "open-fava.sh", "validate-ledger.sh")


def existing_hash(path: Path) -> str | None:
    if path.exists() and not path.is_file():
        raise WorkflowError("unsafe_path", f"Expected a regular file: {path}")
    return digest(path.read_bytes()) if path.exists() else None


def changes_for(root: Path) -> list[dict[str, Any]]:
    baseline = read_json(PLUGIN / "assets/legacy-manifest.json")
    changes: list[dict[str, Any]] = []

    def change(relative: str, content: bytes | None) -> None:
        path = checked_path(root, relative)
        before = existing_hash(path)
        after = digest(content) if content is not None else None
        if before == after:
            return
        known = before is not None and before == baseline.get(relative)
        record: dict[str, Any] = {
            "path": relative,
            "operation": "remove" if content is None else "write",
            "before": before,
            "after": after,
            "classification": "known_legacy"
            if known
            else "customized_or_unknown"
            if before
            else "new",
            "content": content.decode() if content is not None else None,
        }
        if (
            content is not None
            and path.exists()
            and relative in {"AGENTS.md", "README.md", ".gitignore"}
        ):
            record["diff"] = "".join(
                difflib.unified_diff(
                    path.read_text().splitlines(keepends=True),
                    content.decode().splitlines(keepends=True),
                    fromfile=f"a/{relative}",
                    tofile=f"b/{relative}",
                )
            )
        changes.append(record)

    for name in ("AGENTS.md", "README.md"):
        change(name, (TEMPLATE / name).read_bytes())
    change(".gitignore", ignore_contents(root))
    for name in LEGACY_SKILLS:
        directory = checked_path(root, f".agents/skills/{name}")
        if not directory.exists():
            continue
        if not directory.is_dir():
            raise WorkflowError("unsafe_path", f"Expected skill directory: {directory}")
        for path in sorted(directory.rglob("*")):
            relative = path.relative_to(root).as_posix()
            checked_path(root, relative)
            if path.is_file():
                # Arbitrarily named ledger fragments are financial data, even in a skill folder.
                if path.suffix == ".beancount":
                    continue
                # A shared folder can contain unrelated user resources. Retire only
                # manifest-owned paths; their customized contents are still reviewed.
                if relative in baseline:
                    change(relative, None)
    for name in LEGACY_SCRIPTS:
        change(f"scripts/{name}", None)
    change(STATE, json_bytes({"format_version": FORMAT_VERSION}))
    return changes


def legacy_inventory(root: Path) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    """Inspect evidence without rewriting it or accepting unknown formats."""
    relative = "statements/import-status.yml"
    path = checked_path(root, relative)
    status = load_state(path)
    validate_state("status", root, status)
    inputs = {relative: digest(path.read_bytes())}
    mark: list[str] = []
    for group_id, group in status["groups"].items():
        pointer = group["parsed_group"]
        evidence = bounded_path(root, pointer, "statements/parsed")
        if not evidence.is_file():
            raise WorkflowError(
                "missing_evidence", f"{group_id}: missing parsed evidence {pointer}."
            )
        data = load_state(evidence)
        inputs[pointer] = digest(evidence.read_bytes())
        if "statements" in data or "schema_version" in data:
            validate_state("parsed-group", root, data)
            if group.get("legacy", False):
                raise WorkflowError(
                    "invalid_legacy_marker",
                    f"{group_id}: current evidence cannot be marked legacy.",
                )
            continue
        known = (
            all(
                isinstance(data.get(key), str) and data[key]
                for key in (
                    "parse_run_id",
                    "source_file",
                    "source_fingerprint",
                    "source_format",
                    "parsed_at",
                )
            )
            and isinstance(data.get("parser"), (dict, str))
            and isinstance(data.get("extracted_records"), list)
            and all(isinstance(row, dict) for row in data["extracted_records"])
        )
        if not known:
            raise WorkflowError(
                "unsupported_evidence",
                f"{group_id}: unsupported parsed evidence {pointer}; do not mark it legacy.",
            )
        source = data["source_file"]
        if (
            set(group["sources"]) != {source}
            or group["sources"][source]["source_fingerprint"]
            != data["source_fingerprint"]
        ):
            raise WorkflowError(
                "evidence_identity",
                f"{group_id}: evidence identity disagrees with status at {pointer}.",
            )
        if group["current_status"] != "done":
            advice = (
                "This workspace already migrated; recover the import using its compatible workflow or an explicitly reviewed status correction."
                if (root / STATE).exists()
                else "Finish this import with the compatible pre-migration workflow, then retry."
            )
            raise WorkflowError(
                "unfinished_legacy_import",
                f"{group_id}: {source}, status {group['current_status']}, evidence {pointer}. {advice}",
            )
        if not group.get("legacy", False):
            mark.append(group_id)
    return status, inputs, mark


def marker_change(
    root: Path, status: dict[str, Any], groups: list[str]
) -> dict[str, Any]:
    relative = "statements/import-status.yml"
    before_text = checked_path(root, relative).read_text()
    # Preserve original YAML formatting and unrelated fields.
    lines = before_text.splitlines(keepends=True)
    selected = False
    for index, line in enumerate(lines):
        if (
            line.startswith("  ")
            and not line.startswith("   ")
            and line.rstrip().endswith(":")
        ):
            selected = line.strip()[:-1] in groups
        if selected and line.startswith("    current_status:"):
            lines[index] = line + "    legacy: true\n"
        if selected and line.startswith("    legacy: false"):
            lines[index] = ""
    content = "".join(lines)
    expected = {
        **status,
        "groups": {
            key: {**value, **({"legacy": True} if key in groups else {})}
            for key, value in status["groups"].items()
        },
    }
    if yaml.safe_load(content) != expected:
        raise WorkflowError(
            "unsupported_status_layout",
            "Status formatting needs a reviewed normalization before marker migration.",
        )
    return {
        "path": relative,
        "operation": "write",
        "before": digest(before_text.encode()),
        "after": digest(content.encode()),
        "classification": "legacy_status_markers",
        "content": content,
        "diff": "".join(
            difflib.unified_diff(
                before_text.splitlines(keepends=True),
                content.splitlines(keepends=True),
                fromfile=relative,
                tofile=relative,
            )
        ),
    }


def plan_identity(plan: dict[str, Any]) -> str:
    fields = {"workspace": plan["workspace"], "changes": plan["changes"]}
    if "inputs" in plan:
        fields["inputs"] = plan["inputs"]
    return digest(json_bytes(fields))[:24]


def check_inputs(root: Path, journal: dict[str, Any]) -> None:
    legacy_inventory(root)
    changes = {change["path"]: change for change in journal["changes"]}
    for relative, expected in journal.get("inputs", {}).items():
        allowed = {expected}
        if relative in changes:
            allowed.add(changes[relative]["after"])
        if existing_hash(checked_path(root, relative)) not in allowed:
            raise WorkflowError(
                "stale_plan",
                f"Migration input changed: {relative}. Review a fresh migration plan; preserve the existing journal and backups.",
            )


def plan_migration(path: Path) -> dict[str, Any]:
    root = workspace(path, legacy=True)
    status, inputs, mark = legacy_inventory(root)
    changes = [] if (root / STATE).exists() else changes_for(root)
    if mark:
        changes.append(marker_change(root, status, mark))
    if not changes:
        return {
            "status": "ok",
            "workspace": str(root),
            "changes": [],
            "message": "Already migrated; evidence compatibility checked.",
        }
    plan: dict[str, Any] = {
        "workspace": str(root),
        "changes": changes,
        "inputs": inputs,
    }
    plan["plan_id"] = plan_identity(plan)
    return {
        "status": "review_required",
        **plan,
        "message": "Review replacements and retired files. Customized files are backed up, not merged automatically. Apply only after user approval.",
    }


def apply_migration(path: Path, plan_id: str) -> dict[str, object]:
    root = workspace(path, legacy=True)
    if len(plan_id) != 24 or any(c not in "0123456789abcdef" for c in plan_id):
        raise WorkflowError(
            "invalid_plan", "Use the plan_id from the reviewed migration plan."
        )
    directory = checked_path(root, f".auto-bean/migrations/{plan_id}")
    journal_path = checked_path(root, f".auto-bean/migrations/{plan_id}/journal.json")
    if journal_path.exists():
        journal = read_json(journal_path)
        if journal.get("workspace") != str(root) or journal.get("plan_id") != plan_id:
            raise WorkflowError(
                "invalid_journal", "Migration journal does not match this workspace."
            )
        if plan_identity(journal) != plan_id:
            raise WorkflowError(
                "invalid_journal", "The reviewed migration contents changed."
            )
    else:
        plan = plan_migration(root)
        if plan.get("plan_id") != plan_id:
            raise WorkflowError(
                "stale_plan",
                "Workspace changed. Review a fresh migration plan before applying.",
            )
        # Validate before removing old execution surfaces. No financial state is rewritten.
        environment = ensure_runtime(root)
        validate(root, environment)
        check_inputs(root, plan)
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory.chmod(0o700)
        journal = {**plan, "completed": [], "status": "applying"}
        atomic_write(journal_path, json_bytes(journal))

    check_inputs(root, journal)
    environment = ensure_runtime(root)
    validate(root, environment)
    changes = journal["changes"]
    # Check every remaining path before applying any more work. Detect concurrent edits.
    for change in changes:
        target = checked_path(root, change["path"])
        actual = existing_hash(target)
        allowed = (
            {change["after"]}
            if change["path"] in journal["completed"]
            else {change["before"], change["after"]}
        )
        if actual not in allowed:
            raise WorkflowError(
                "migration_conflict",
                f"Changed during migration: {change['path']}. Resolve against the backup before resuming.",
            )

    # Back up all originals before the first mutation. Journal survives interrupted execution.
    for change in changes:
        if change["before"] is None:
            continue
        backup = checked_path(
            root, f".auto-bean/migrations/{plan_id}/backup/{change['path']}"
        )
        if backup.exists():
            if existing_hash(backup) != change["before"]:
                raise WorkflowError("invalid_backup", f"Backup changed: {backup}")
            continue
        target = checked_path(root, change["path"])
        if existing_hash(target) != change["before"]:
            raise WorkflowError(
                "missing_backup", f"Original backup unavailable for {change['path']}."
            )
        original = target.read_bytes()
        if digest(original) != change["before"]:
            raise WorkflowError(
                "migration_conflict", f"Changed while backing up: {change['path']}."
            )
        atomic_write(backup, original)

    for change in changes:
        relative = change["path"]
        if relative in journal["completed"]:
            continue
        target = checked_path(root, relative)
        actual = existing_hash(target)
        if actual not in {change["before"], change["after"]}:
            raise WorkflowError(
                "migration_conflict", f"Changed before applying: {relative}."
            )
        if actual != change["after"]:
            if change["operation"] == "remove":
                target.unlink()
            else:
                atomic_write(target, change["content"].encode())
        journal["completed"].append(relative)
        atomic_write(journal_path, json_bytes(journal))
    validate(root, environment)
    journal["status"] = "complete"
    atomic_write(journal_path, json_bytes(journal))
    return {
        "status": "ok",
        "workspace": str(root),
        "backup": str(directory / "backup"),
        "message": "Migration complete. Review the diff and preserved customizations before committing; nothing was committed or pushed.",
    }
