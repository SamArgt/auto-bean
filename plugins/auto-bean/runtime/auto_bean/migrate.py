from __future__ import annotations

import difflib
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


def plan_migration(path: Path) -> dict[str, Any]:
    root = workspace(path, legacy=True)
    if (root / STATE).exists():
        return {
            "status": "ok",
            "workspace": str(root),
            "changes": [],
            "message": "Already migrated.",
        }
    plan: dict[str, Any] = {"workspace": str(root), "changes": changes_for(root)}
    plan["plan_id"] = digest(json_bytes(plan))[:24]
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
        if (
            digest(
                json_bytes({"workspace": str(root), "changes": journal.get("changes")})
            )[:24]
            != plan_id
        ):
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
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory.chmod(0o700)
        journal = {**plan, "completed": [], "status": "applying"}
        atomic_write(journal_path, json_bytes(journal))

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
