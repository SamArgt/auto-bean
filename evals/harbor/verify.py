"""Trusted semantic graders. No agent code or workspace Python is imported."""

from __future__ import annotations

import argparse
import copy
from collections import Counter, defaultdict
from contextvars import ContextVar
from datetime import date, datetime
from decimal import Decimal
import json
import os
import glob
import html
import inspect
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from beancount import loader
from beancount.core.data import Balance, Document, Open, Price, Transaction
from beancount.parser import parser as bean_parser

# These imports resolve to the verifier's immutable bundle, never the ledger.
from auto_bean.validation import (
    session_members,
    status_members,
    session_status as _session_status,
    load_state,
    validate_state as _validate_state,
)
from evals.harbor.fixtures import OPENING, SOURCES, sha256, write_json
from evals.harbor.capture import write_review_html
from evals.harbor.trace import grade_trace, snapshot_reader

EXPECTED_POSTINGS = (
    ("2026-01-05", (("Assets:Checking", "-25", "EUR"), ("Expenses:Food", "25", "EUR"))),
    (
        "2026-01-10",
        (("Assets:Checking", "-100", "EUR"), ("Assets:Savings", "100", "EUR")),
    ),
    (
        "2026-01-15",
        (("Assets:Checking", "-5", "EUR"), ("Expenses:Bank-Fees", "5", "EUR")),
    ),
    ("2026-01-31", (("Assets:Savings", "2", "EUR"), ("Income:Interest", "-2", "EUR"))),
)

_STATE_CHECKS: ContextVar[list[dict[str, Any]] | None] = ContextVar(
    "state_checks", default=None
)


def validate_state(kind: str, root: Path, data: dict[str, Any]) -> None:
    _validate_state(kind, root, data)
    require(True, f"Invalid {kind} schema or state")


def session_status(session: dict[str, Any], status: dict[str, Any]) -> None:
    _session_status(session, status)
    require(True, "Session and status are inconsistent")


def require(condition: object, message: str) -> None:
    checks = _STATE_CHECKS.get()
    if checks is not None:
        frame = inspect.currentframe()
        caller = frame.f_back if frame is not None else None
        context: dict[str, str] = {}
        if caller is not None:
            # Restrict context to subject identifiers. Do not dump workspace data.
            for key in ("raw", "source", "relative", "phase", "subject", "match"):
                value = caller.f_locals.get(key)
                if isinstance(value, str):
                    context[key] = value
        observed: dict[str, Any] = {}
        if not condition and caller is not None:
            doc = caller.f_locals.get("doc", caller.f_locals.get("parsed", {}))
            if isinstance(doc, dict) and isinstance(doc.get("review"), dict):
                observed["validation"] = doc["review"].get("validation")
                observed["approval"] = doc["review"].get("approval")
            account = caller.f_locals.get("account", {})
            if isinstance(account, dict) and isinstance(account.get("review"), dict):
                observed["proposed_directives"] = account["review"].get(
                    "proposed_directives"
                )
        checks.append(
            {
                "scope": "state",
                "status": "passed" if condition else "failed",
                "failure_message": message,
                "location": {
                    "file": "evals/harbor/verify.py",
                    "function": caller.f_code.co_name if caller else "unknown",
                    "line": caller.f_lineno if caller else None,
                },
                "context": context,
                "observed": observed,
            }
        )
        del caller, frame
    if not condition:
        raise AssertionError(message)


def finish_report(
    report: dict[str, Any], state_checks: list[dict[str, Any]], trace: dict[str, Any]
) -> None:
    """Expose all executed checks without changing the binary grading policy."""
    checks = list(state_checks)
    checks.extend(
        {
            "scope": "trace",
            "status": "passed" if check["passed"] else "failed",
            "requirement": check["requirement"],
            "evidence": check.get("evidence", []),
            "detail": check.get("detail", ""),
        }
        for check in trace.get("checks", [])
    )
    if trace.get("failure"):
        checks.append(
            {
                "scope": "trace",
                "status": "error",
                "requirement": "Load and evaluate native trace",
                "detail": trace["failure"],
            }
        )
        checks.append(
            {
                "scope": "trace",
                "status": "skipped",
                "requirement": "Remaining trace checks",
                "detail": "Trace input could not be loaded. No trace assertions ran.",
            }
        )
    report["schema_version"] = 2
    report["checks"] = checks
    report["check_summary"] = {
        scope: {
            status: sum(c["scope"] == scope and c["status"] == status for c in checks)
            for status in ("passed", "failed", "error", "skipped")
        }
        for scope in ("state", "trace")
    }
    report["coverage_note"] = (
        "State checks stop at the first failed assertion or exception. "
        "Skipped rows describe unexecuted check groups, not individual check counts. "
        "Assertion labels are failure messages; passed means that condition was absent. "
        "Trace checks run independently. State-dependent trace expectations are only "
        "available after state checks pass."
    )


def write_report_markdown(path: Path, report: dict[str, Any]) -> None:
    def cell(value: object) -> str:
        return (
            html.escape(str(value))
            .replace("|", "\\|")
            .replace("\n", " ")
            .replace("\r", " ")
        )

    lines = [
        "# Verifier report",
        "",
        f"Phase: **{report['phase']}**. Result: **{'PASS' if report['passed'] else 'FAIL'}**.",
        f"Trace policy: `{report['trace_policy']}`.",
        "",
        "| Scope | Passed | Failed | Errors | Skipped groups |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for scope, counts in report["check_summary"].items():
        lines.append(
            f"| {scope} | {counts['passed']} | {counts['failed']} | "
            f"{counts['error']} | {counts['skipped']} |"
        )
    lines += ["", report["coverage_note"]]
    icons = {"passed": "✅", "failed": "❌", "error": "⚠️", "skipped": "⏭️"}
    ordered = sorted(
        enumerate(report["checks"], 1),
        key=lambda item: {"failed": 0, "error": 1, "skipped": 2, "passed": 3}[
            item[1]["status"]
        ],
    )
    previous = None
    for index, check in ordered:
        if check["status"] != previous:
            previous = check["status"]
            lines += [
                "",
                f"## {icons[previous]} {previous.title()}",
                "",
                "| # | Scope | Assertion failure message / requirement | Evidence or detail |",
                "| ---: | --- | --- | --- |",
            ]
        detail = []
        if location := check.get("location"):
            detail.append(
                f"{location['file']}:{location['line']} ({location['function']})"
            )
        detail.extend(
            f"{key}={value}" for key, value in check.get("context", {}).items()
        )
        detail.extend(check.get("evidence", []))
        if check.get("detail"):
            detail.append(check["detail"])
        if check.get("observed"):
            detail.append(json.dumps(check["observed"], sort_keys=True))
        label = check.get("failure_message", check.get("requirement", ""))
        lines.append(
            f"| {index} | {check['scope']} | {cell(label)} | "
            f"{cell('; '.join(detail))} |"
        )
    path.write_text("\n".join(lines) + "\n")


def section_content(text: str, heading: str) -> str:
    match = re.search(
        r"^## " + re.escape(heading) + r"[ \t]*\n(.*?)(?=^## |\Z)", text, re.M | re.S
    )
    return match[1].strip() if match else ""


def inside(root: Path, relative: str) -> Path:
    path = root / relative
    require(
        not path.is_symlink() and path.resolve().is_relative_to(root.resolve()),
        f"Unsafe path: {relative}",
    )
    require(path.is_file(), f"Missing file: {relative}")
    return path


def git(root: Path, *args: str) -> str:
    # Ignore user/global configuration when inspecting transferred Git metadata.
    return subprocess.check_output(
        [
            "git",
            "-c",
            f"safe.directory={root}",
            "-c",
            "core.hooksPath=/dev/null",
            *args,
        ],
        cwd=root,
        text=True,
    ).strip()


def load_ledger(root: Path) -> tuple[list[Any], dict[str, Any]]:
    # Beancount plugin directives execute Python. These fixtures need none.
    pending = [root / "ledger.beancount", *root.rglob("*.beancount")]
    checked: set[Path] = set()
    while pending:
        path = pending.pop()
        require(path.resolve().is_relative_to(root.resolve()), "Include escapes ledger")
        relative = path.absolute().relative_to(root.absolute())
        require(
            not any(
                (root / Path(*relative.parts[:i])).is_symlink()
                for i in range(1, len(relative.parts) + 1)
            ),
            "Ledger contains a symlink",
        )
        require(path.is_file(), "Missing ledger input")
        if path.resolve() in checked:
            continue
        checked.add(path.resolve())
        for line in path.read_text().splitlines():
            require(
                not re.match(r"\s*plugin\s", line),
                "Unexpected executable ledger plugin",
            )
            if re.match(r"\s*include\s", line):
                match = re.fullmatch(
                    r'\s*include\s+("(?:[^"\\]|\\.)*")\s*(?:;.*)?', line
                )
                require(match is not None, "Unsupported include syntax")
                assert match is not None
                target = path.parent / json.loads(match[1])
                require(
                    target.resolve().is_relative_to(root.resolve()),
                    "Include escapes ledger",
                )
                # Follow every actual input, including non-.beancount suffixes.
                matches = glob.glob(str(target))
                require(matches, "Missing included ledger input")
                pending.extend(Path(item) for item in matches)
    entries, errors, options = loader.load_file(str(root / "ledger.beancount"))
    require(not errors, f"Ledger validation returned {len(errors)} errors")
    require(options["operating_currency"] == ["EUR"], "Operating currency must be EUR")
    return list(entries), dict(options)


def signature(entry: Any) -> tuple[str, tuple[tuple[str, str, str], ...]]:
    return entry.date.isoformat(), tuple(
        sorted(
            (
                posting.account,
                str(posting.units.number.normalize()),
                posting.units.currency,
            )
            for posting in entry.postings
        )
    )


def economic_key(entry: Any) -> tuple[str, tuple[tuple[str, Decimal, str], ...]]:
    day, postings = signature(entry)
    return day, tuple(
        (account, Decimal(amount), currency) for account, amount, currency in postings
    )


def runtime_check(evidence: Path) -> None:
    record = json.loads(inside(evidence, "runtime.json").read_text())
    require(
        record.get("validated") is True and record.get("runtime_present") is True,
        "Managed runtime did not validate the actual ledger",
    )


def init_checks(root: Path, plugin: Path, evidence: Path) -> None:
    marker = load_state(inside(root, ".auto-bean/workspace.json"))
    require(marker == {"format_version": 1}, "Unexpected workspace marker")
    entries, _ = load_ledger(root)
    require(
        not any(isinstance(entry, Transaction) for entry in entries),
        "Initialization invented transactions",
    )
    require(
        {
            (entry.account, tuple(entry.currencies or []))
            for entry in entries
            if isinstance(entry, Open)
        }
        == {("Assets:Checking", ("EUR",)), ("Equity:Opening-Balances", ("EUR",))},
        "Initialization changed default accounts",
    )
    for path in (plugin / "assets/workspace_template").rglob("*"):
        if path.is_file():
            inside(
                root, path.relative_to(plugin / "assets/workspace_template").as_posix()
            )
    for name in ("statements/raw", "statements/parsed", ".auto-bean/memory"):
        require((root / name).is_dir(), f"Missing scaffold directory: {name}")
    require(
        git(root, "rev-list", "--count", "HEAD") == "1", "Expected one initial commit"
    )
    require(
        not git(root, "status", "--porcelain"),
        "Initialized ledger has uncommitted files",
    )
    tracked = git(root, "ls-files").splitlines()
    for required in (
        "ledger.beancount",
        ".auto-bean/workspace.json",
        ".auto-bean/memory/MEMORY.md",
    ):
        require(required in tracked, f"Scaffold is not tracked: {required}")
    require(
        not any(
            "runtime/" in path or "SKILL.md" in path or ".venv/" in path
            for path in tracked
        ),
        "Initial commit contains product skills or runtime caches",
    )
    for name in (".agents", ".codex", "scripts", ".venv"):
        require(
            not (root / name).exists(), f"Product content copied into workspace: {name}"
        )
    for path in (root / ".auto-bean/memory").rglob("*.json"):
        validate_state("memory", root, load_state(path))
    runtime_check(evidence)


def source_checks(root: Path, expected: dict[str, Any]) -> dict[str, Any]:
    for relative, digest in {**expected["sources"], **expected["preserved"]}.items():
        require(
            sha256(inside(root, relative)) == digest,
            f"Preserved file changed: {relative}",
        )
    require(
        git(root, "rev-parse", "HEAD") == expected["head"],
        "Import changed existing Git history",
    )
    require(
        not git(root, "diff", "--cached", "--name-only"), "Import staged user files"
    )
    status = load_state(inside(root, "statements/import-status.yml"))
    validate_state("status", root, status)
    require(
        set(status_members(status)) == set(SOURCES),
        "Status must describe exactly the two raw statements",
    )
    return status


def parsed_source(root: Path, path: str, source: str) -> dict[str, Any]:
    group = load_state(inside(root, path))
    validate_state("parsed-group", root, group)
    status = load_state(inside(root, "statements/import-status.yml"))
    entry = status["groups"].get(group["group_id"], {})
    require(
        entry.get("parsed_group") == path
        and set(entry.get("sources", {}))
        == {d["source_file"] for d in group["statements"]},
        "Parsed group membership differs from status",
    )
    return next(d for d in group["statements"] if d["source_file"] == source)


def financial_hashes(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): sha256(p)
        for p in root.rglob("*.beancount")
        if ".auto-bean" not in p.relative_to(root).parts
    }


def account_decisions(data: dict[str, Any]) -> dict[str, Any]:
    """Project inline decisions without executing submitted workspace code."""
    return {
        account["account_id"]: account["review"]
        for account in data["statement_metadata"]["accounts"]
        if "review" in account
    }


def sole_account_review(data: dict[str, Any]) -> dict[str, Any]:
    """These sources each have one account; its extracted ID is not prescribed."""
    accounts = data["statement_metadata"]["accounts"]
    require(len(accounts) == 1, "Each fixture has exactly one account")
    return dict(accounts[0].get("review", {}))


def supporting_directives(root: Path, doc: dict[str, Any]) -> list[Any]:
    """Parse only fixture-supported documents and optional closing assertions."""
    raw = doc["source_file"]
    account = "Assets:Checking" if raw == SOURCES[0] else "Assets:Savings"
    closing = Decimal(870 if raw == SOURCES[0] else 602)
    directives = sole_account_review(doc).get("proposed_directives", [])
    entries = []
    for directive in directives:
        # Reject options/includes/plugins before parsing. Each proposal is one
        # dated directive, not an executable ledger fragment or extra metadata.
        require(
            re.fullmatch(
                r"2026-\d{2}-\d{2}[ \t]+(?:document|balance)[ \t]+[^\r\n]+", directive
            )
            is not None,
            "Unsupported proposed supporting directive",
        )
        parsed, errors, _ = bean_parser.parse_string(
            directive + "\n", report_filename=str(root / "ledger.beancount")
        )
        require(not errors and len(parsed) == 1, "Invalid supporting directive")
        entry = parsed[0]
        require(
            isinstance(entry, (Document, Balance)),
            "Unsupported supporting directive type",
        )
        assert isinstance(entry, (Document, Balance))
        require(entry.account == account, "Supporting directive targets wrong account")
        if isinstance(entry, Document):
            filename = re.search(r'"(?:[^"\\]|\\.)*"', directive)
            require(
                entry.date == date(2026, 1, 31)
                and filename is not None
                and json.loads(filename[0]) == raw
                and Path(entry.filename) == (root / raw).absolute()
                and not entry.tags
                and not entry.links,
                "Document directive must identify its original statement at period end",
            )
        else:
            require(
                isinstance(entry, Balance)
                and entry.date == date(2026, 2, 1)
                and entry.amount.number == closing
                and entry.amount.currency == "EUR"
                and entry.tolerance is None,
                "Balance directive must assert the exact next-day closing balance",
            )
        entries.append(entry)
    require(
        sum(isinstance(e, Document) for e in entries) == 1
        and sum(isinstance(e, Balance) for e in entries) <= 1,
        "Expected one source document and at most one closing assertion",
    )
    return entries


def review_validation(root: Path, doc: dict[str, Any]) -> None:
    """A blocked review can retain a failed report; it cannot certify writes."""
    validation = doc["review"].get("validation")
    if validation is None:
        return
    unresolved = any(
        account.get("review", {}).get("state") == "needs_input"
        for account in doc["statement_metadata"]["accounts"]
    ) or any(
        row.get("review", {}).get("state") == "needs_input"
        or row.get("review", {}).get("disposition") == "hold"
        for row in doc["extracted_records"]
    )
    require(
        validation["stage"] == "review" and validation["digest"] == material_hash(doc),
        "Premature written or stale review validation",
    )
    if validation["state"] == "failed":
        require(
            unresolved
            and bool(validation["errors"])
            and validation["records_checked"] == 0
            and not validation["ledger_hashes"]
            and not validation["balances"],
            "Failed readiness validation must not claim checked ledger writes",
        )
    else:
        require(
            not unresolved
            and validation["state"] == "passed"
            and not validation["errors"]
            and validation["records_checked"] == len(doc["extracted_records"])
            and validation["ledger_hashes"] == financial_hashes(root),
            "Review validation does not describe the current candidate and baseline",
        )


def transaction_decisions(data: dict[str, Any]) -> dict[str, Any]:
    return {
        record["record_id"]: record["review"]
        for record in data["extracted_records"]
        if "review" in record
    }


def material_hash(data: dict[str, Any]) -> str:
    from hashlib import sha256 as hash_bytes

    value = {k: v for k, v in data.items() if k != "review"}
    value["review"] = {
        "processing": {
            k: v
            for k, v in data["review"]["processing"].items()
            if k in {"needs_input", "suggestions", "answer"}
        }
    }
    return hash_bytes(
        (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    ).hexdigest()


def string_values(value: Any) -> set[str]:
    """Accept equivalent source/audit layouts without accepting vague prose."""
    if isinstance(value, str):
        return {value}
    if isinstance(value, dict):
        return set().union(*(string_values(v) for v in value.values()))
    if isinstance(value, list):
        return set().union(*(string_values(v) for v in value))
    return set()


def memory_checks(
    root: Path, session: dict[str, Any], documents: dict[str, Any], *, approved: bool
) -> None:
    """Check actual reusable records, never a claimed completion marker."""
    memory = root / ".auto-bean/memory"
    files = {
        p.relative_to(memory).as_posix(): load_state(p) for p in memory.rglob("*.json")
    }
    for data in files.values():
        validate_state("memory", root, data)
    if not approved:
        for data in files.values():
            if data["memory_type"] in {
                "account_mapping",
                "category_mapping",
                "transfer_detection",
                "deduplication_decision",
                "commodity_price_source",
            }:
                require(
                    not data["records"], "Unapplied decisions entered governed memory"
                )
        return

    expected_records = (
        ("account_mappings.json", SOURCES[0], "CHECKING-TEST", "Assets:Checking"),
        ("account_mappings.json", SOURCES[1], "SAVINGS-TEST", "Assets:Savings"),
        ("category_mappings.json", SOURCES[0], "Example Market", "Expenses:Food"),
    )
    parsed_paths = {
        m["source_file"]: m["parsed_group"] for m in session_members(session)
    }
    for filename, source, match, account in expected_records:
        records = files[filename]["records"]
        field = (
            "beancount_account"
            if filename == "account_mappings.json"
            else "posting_account"
        )
        matching = [r for r in records if match in string_values(r["decision"])]
        require(
            len(matching) == 1 and matching[0]["decision"].get(field) == account,
            f"Missing, conflicting or duplicated eligible memory for {match}",
        )
        record = matching[0]
        require(
            record.get("record_id")
            and record.get("review_state") in {"approved", "confirmed"},
            "Governed memory lacks stable identity or accepted review state",
        )
        scope = string_values(record["scope"])
        external = "CHECKING-TEST" if source == SOURCES[0] else "SAVINGS-TEST"
        require(
            {external, "EUR", "Alex Example"} <= scope,
            "Governed memory scope is broader than the accepted account evidence",
        )
        provenance = string_values(record["source"])
        require(
            bool({source, parsed_paths[source]} & provenance)
            and documents[source]["source_fingerprint"] in provenance,
            "Governed memory lacks exact source provenance",
        )
        audit = string_values(record["audit"])
        doc = documents[source]
        validation = doc["review"].get("validation", {})
        require(
            {
                session["session_id"],
                material_hash(doc),
                validation.get("checked_at", ""),
            }
            <= audit
            and validation.get("state") == "passed"
            and validation.get("stage") == "written",
            "Governed memory lacks written ledger validation provenance",
        )
        require(
            datetime.fromisoformat(record["created_at"])
            >= datetime.fromisoformat(validation["checked_at"])
            and datetime.fromisoformat(record["updated_at"])
            >= datetime.fromisoformat(record["created_at"]),
            "Governed memory was learned before written validation",
        )


def financial_checks(root: Path, documents: dict[str, Any]) -> None:
    entries, _ = load_ledger(root)
    expected_support = [
        directive
        for doc in documents.values()
        for directive in supporting_directives(root, doc)
    ]

    def support_key(entry: Any) -> tuple[Any, ...]:
        if isinstance(entry, Document):
            return (
                "document",
                entry.date,
                entry.account,
                entry.filename,
                entry.tags,
                entry.links,
            )
        return ("balance", entry.date, entry.account, entry.amount, entry.tolerance)

    require(
        Counter(support_key(e) for e in entries if isinstance(e, (Document, Balance)))
        == Counter(support_key(e) for e in expected_support),
        "Written supporting directives differ from the reviewed proposal",
    )
    require(
        {(e.account, tuple(e.currencies or [])) for e in entries if isinstance(e, Open)}
        == {
            (name, ("EUR",))
            for name in (
                "Assets:Checking",
                "Assets:Savings",
                "Expenses:Food",
                "Expenses:Bank-Fees",
                "Income:Interest",
                "Equity:Opening-Balances",
            )
        },
        "Import created or changed account definitions",
    )
    require(
        not any(isinstance(e, Price) for e in entries),
        "EUR-only import invented price directives",
    )
    require(
        all(isinstance(e, (Open, Transaction, Document, Balance)) for e in entries),
        "Ledger contains an unreviewed supporting directive",
    )
    transactions = [e for e in entries if isinstance(e, Transaction)]
    opening = [e for e in transactions if e.date == date(2025, 12, 31)]
    require(
        len(opening) == 1
        and (root / "beancount/opening-balances.beancount").read_text() == OPENING,
        "Existing opening transaction was changed",
    )
    current = [e for e in transactions if e not in opening]
    expected_keys = Counter(
        (day, tuple((a, Decimal(n), c) for a, n, c in sorted(postings)))
        for day, postings in EXPECTED_POSTINGS
    )
    require(
        Counter(economic_key(e) for e in current) == expected_keys,
        "Wrong economic transactions, dates, accounts, amounts, or duplicate transfer",
    )
    require(all(e.flag == "*" for e in current), "Unexpected transaction flags")
    balances: dict[str, Decimal] = defaultdict(Decimal)
    for entry in transactions:
        for posting in entry.postings:
            units = posting.units
            require(
                units is not None and isinstance(units.number, Decimal),
                "Unexpected incomplete posting",
            )
            assert units is not None and isinstance(units.number, Decimal)
            if units.currency == "EUR":
                balances[posting.account] += units.number
    require(
        balances["Assets:Checking"] == Decimal(870)
        and balances["Assets:Savings"] == Decimal(602),
        "Closing balances do not reconcile",
    )
    for raw, doc in documents.items():
        for row in doc["extracted_records"]:
            matches = [
                e for e in current if e.date.isoformat() == row["transaction_date"]
            ]
            require(
                len(matches) == 1, "Cannot locate source record economic transaction"
            )
            identities = {
                tuple(
                    meta.get(prefix + key)
                    for key in (
                        "source",
                        "source_fingerprint",
                        "account_id",
                        "record_id",
                    )
                )
                for meta in [
                    matches[0].meta,
                    *(p.meta or {} for p in matches[0].postings),
                ]
                for prefix in ("", "peer_")
            }
            require(
                (raw, doc["source_fingerprint"], row["account_id"], row["record_id"])
                in identities,
                "Transaction lacks full source-record provenance",
            )


def import_checks(
    root: Path,
    plugin: Path,
    evidence: Path,
    expected: dict[str, Any],
    phase: str,
    *,
    explicit_group: bool = True,
) -> None:
    import hashlib
    import tempfile

    del plugin
    status = source_checks(root, expected)
    wanted = "final_review" if phase == "review" else "done"
    require(
        all(i["current_status"] == wanted for i in status_members(status).values()),
        f"Both statements must be {wanted}",
    )
    sessions = list((root / ".auto-bean/import-sessions").glob("*.json"))
    require(len(sessions) == 1, "Exactly one explicit import session is required")
    session = load_state(sessions[0])
    validate_state("session", root, session)
    session_status(session, status)
    if explicit_group:
        require(
            len(session["groups"]) == 1
            and session["groups"][0]["name"] == "January accounts"
            and session["groups"][0]["origin"] == "user",
            "Explicit January accounts group was not preserved",
        )
    require(
        {i["source_file"]: i["parsed_group"] for i in session_members(session)}
        == {raw: i["parsed_group"] for raw, i in status_members(status).items()},
        "Session mixing or mismatched membership",
    )
    documents = {}
    for raw, item in status_members(status).items():
        parsed = parsed_source(root, item["parsed_group"], raw)
        validate_state("parsed", root, parsed)
        require(
            parsed.get("schema_version") == 2
            and parsed["extraction_state"] == "complete"
            and parsed["document_kind"] == "statement",
            "Expected complete v2 evidence",
        )
        fingerprint = "sha256:" + expected["sources"][raw]
        require(
            parsed["source_file"] == raw
            and parsed["source_fingerprint"]
            == item["source_fingerprint"]
            == fingerprint,
            "Parsed source identity mismatch",
        )
        accounts = parsed["statement_metadata"]["accounts"]
        require(len(accounts) == 1, "Each fixture has exactly one account")
        account = accounts[0]
        checking = raw.endswith("checking.csv")
        ledger = "Assets:Checking" if checking else "Assets:Savings"
        require(account["primary_currency"] == "EUR", "Wrong statement currency")
        supporting_directives(root, parsed)
        for key, amount in (
            ("opening_balance", "1000" if checking else "500"),
            ("closing_balance", "870" if checking else "602"),
        ):
            require(
                Decimal(account[key]["amount"]) == Decimal(amount)
                and account[key]["currency"] == "EUR",
                f"Wrong extracted {key}",
            )
        expected_rows = (
            [
                ("2026-01-05", Decimal(-25)),
                ("2026-01-10", Decimal(-100)),
                ("2026-01-15", Decimal(-5)),
            ]
            if checking
            else [("2026-01-10", Decimal(100)), ("2026-01-31", Decimal(2))]
        )
        records = parsed["extracted_records"]
        require(
            Counter((r["transaction_date"], Decimal(r["amount"])) for r in records)
            == Counter(expected_rows),
            "Raw source rows were lost, invented, or changed",
        )
        descriptions = (
            {
                "2026-01-05": "Example Market",
                "2026-01-10": "Transfer to own SAVINGS-TEST",
                "2026-01-15": "Monthly bank fee",
            }
            if checking
            else {
                "2026-01-10": "From own CHECKING-TEST",
                "2026-01-31": "Savings interest",
            }
        )
        require(
            all(
                r["description"] == descriptions[r["transaction_date"]]
                and r["currency"] == "EUR"
                and r["account_id"] == account["account_id"]
                for r in records
            ),
            "Extracted source descriptions, currency or account changed",
        )
        review = parsed["review"]
        require(
            review["processing"]["outcome"] == "complete"
            and any("docling" in e.lower() for e in review["processing"]["evidence"]),
            "No completed extraction evidence",
        )
        require(
            account.get("review", {}).get("ledger_account") == ledger,
            "Wrong account mapping",
        )
        require(
            not review["processing"].get("needs_input", False)
            and all(
                a["state"] != "needs_input" for a in account_decisions(parsed).values()
            ),
            "Unresolved account or statement input",
        )
        require(
            set(transaction_decisions(parsed)) == {r["record_id"] for r in records},
            "Missing or duplicate transaction decisions",
        )
        for row in records:
            decision = row["review"]
            require(
                decision["state"] != "needs_input"
                and decision["disposition"] in {"post", "paired_transfer"},
                "Held or omitted source row",
            )
            expected_postings = next(
                postings
                for day, postings in EXPECTED_POSTINGS
                if day == row["transaction_date"]
            )
            require(
                (
                    not decision["postings"]
                    and decision["disposition"] == "paired_transfer"
                    and decision.get("posting_owner") != raw
                )
                or Counter(
                    (p["account"], Decimal(p["amount"]), p["currency"])
                    for p in decision["postings"]
                )
                == Counter((a, Decimal(n), c) for a, n, c in expected_postings),
                "Wrong structured postings",
            )
            if row["transaction_date"] == "2026-01-10":
                require(
                    decision["disposition"] == "paired_transfer"
                    and decision.get("posting_owner") == SOURCES[0]
                    and len(decision.get("linked_records", [])) == 1,
                    "Transfer lacks single owner or paired source",
                )
            else:
                require(
                    decision["disposition"] == "post",
                    "Unexpected non-transfer disposition",
                )
        documents[raw] = parsed
    for raw, doc in documents.items():
        for decision in transaction_decisions(doc).values():
            for link in decision.get("linked_records", []):
                peer = documents.get(link["source_file"], {})
                require(
                    any(
                        r["record_id"] == link["record_id"]
                        and r["account_id"] == link["account_id"]
                        for r in peer.get("extracted_records", [])
                    ),
                    "Invalid cross-statement record reference",
                )
    # A non-owner may delegate its postings to the linked owner. Resolve that
    # reference independently; never accept an empty proposal without the exact
    # owner economics and reciprocal evidence.
    for raw, doc in documents.items():
        for row in doc["extracted_records"]:
            decision = row["review"]
            if decision["disposition"] != "paired_transfer":
                continue
            link = decision["linked_records"][0]
            peer = documents[link["source_file"]]
            peer_decision = transaction_decisions(peer)[link["record_id"]]
            require(
                link["source_file"] != raw
                and peer_decision["disposition"] == "paired_transfer"
                and peer_decision.get("posting_owner") == decision["posting_owner"]
                and peer_decision["linked_records"]
                == [
                    {
                        "source_file": raw,
                        "account_id": row["account_id"],
                        "record_id": row["record_id"],
                    }
                ],
                "Transfer owner link is not reciprocal",
            )
            if decision["posting_owner"] == raw:
                continue
            require(
                link["source_file"] == decision["posting_owner"]
                and Counter(
                    (p["account"], Decimal(p["amount"]), p["currency"])
                    for p in peer_decision["postings"]
                )
                == Counter((a, Decimal(n), c) for a, n, c in EXPECTED_POSTINGS[1][1]),
                "Transfer owner is missing exact structured postings",
            )
    checkpoint = load_state(inside(evidence, "review.json"))
    require(
        checkpoint["session_id"] == session["session_id"], "Checkpoint session mismatch"
    )
    base = checkpoint["baseline_contents"]
    require(
        {k: hashlib.sha256(v.encode()).hexdigest() for k, v in base.items()}
        == expected["financial_hashes"],
        "Review baseline differs from independent fixture",
    )
    require(
        checkpoint["financial_hashes"] == expected["financial_hashes"],
        "Ledger writes occurred before approval",
    )
    if phase == "review":
        require(
            financial_hashes(root) == expected["financial_hashes"],
            "Ledger writes occurred before approval",
        )
    require(
        set(checkpoint["documents"]) == set(documents)
        and checkpoint["session"]["groups"] == session["groups"],
        "Reviewed statement membership changed",
    )
    require(
        checkpoint["session"]["groups"] == session["groups"], "Reviewed groups changed"
    )
    for raw, doc in documents.items():
        reviewed = checkpoint["documents"][raw]
        require(
            material_hash(doc)
            == material_hash(reviewed)
            == checkpoint["review_digests"][raw],
            "Reviewed transaction evidence changed after review",
        )
        approval = doc["review"].get("approval")
        validation = doc["review"].get("validation")
        # This headless task authorizes writes through its explicit user turn and
        # immutable review checkpoint. Agent-authored approval JSON is not proof.
        require(approval is None, "Fabricated panel approval in chat-only task")
        if phase == "review":
            require(
                validation is None
                or (
                    validation["stage"] == "review"
                    and validation["state"] == "passed"
                    and validation["digest"] == material_hash(doc)
                ),
                "Premature or fabricated write validation",
            )
        else:
            require(
                validation is not None
                and validation["stage"] == "written"
                and validation["state"] == "passed"
                and validation["digest"] == material_hash(doc)
                and validation["records_checked"] == len(doc["extracted_records"])
                and not validation["errors"],
                "Missing successful written transaction validation",
            )
            require(
                datetime.fromisoformat(checkpoint["captured_at"])
                <= datetime.fromisoformat(validation["checked_at"]),
                "Written validation predates review",
            )
            require(
                validation["ledger_hashes"] == financial_hashes(root),
                "Validation does not describe current canonical ledger",
            )
            account = doc["statement_metadata"]["accounts"][0]
            expected_balance = Decimal(account["closing_balance"]["amount"])
            balances = validation["balances"]
            require(
                any(
                    b["account_id"] == account["account_id"]
                    and b["date"] == account["closing_balance"]["date"]
                    and b["currency"] == "EUR"
                    and b["state"] == "matched"
                    and Decimal(b["expected"])
                    == Decimal(b["actual"])
                    == expected_balance
                    for b in balances
                ),
                "Missing checked final account balance",
            )
    # Independently render reviewed postings in verifier-owned temporary storage.
    # Submitted workspace Python and claimed validation are never executed/trusted.
    with tempfile.TemporaryDirectory(prefix="harbor-verifier-") as temporary:
        proposed = Path(temporary)
        for relative, content in base.items():
            target = proposed / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        for relative in SOURCES:
            target = proposed / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(inside(root, relative).read_bytes())
        output = proposed / "beancount/reviewed.beancount"
        output.write_text(
            render_reviewed_transactions(checkpoint["documents"])
            + render_supporting_directives(proposed, checkpoint["documents"])
        )
        with (proposed / "ledger.beancount").open("a") as stream:
            stream.write('\ninclude "beancount/reviewed.beancount"\n')
        financial_checks(proposed, documents)
        if phase == "approve":
            financial_checks(root, documents)
    if phase == "approve":
        require(
            session["price_runs"]
            and all(
                r["state"] == "no_op"
                and r["preflight"] == "passed"
                and r["preflight_job_count"] == 0
                and r["execution"]["state"] == "complete"
                and r["execution"]["exit_code"] == 0
                and not r["jobs"]
                and not r["required_commodities"]
                for r in session["price_runs"]
            ),
            "Missing structured prices stage zero-job outcome",
        )
    memory_checks(root, session, documents, approved=phase == "approve")
    response = inside(evidence, "last-response.txt").read_text().strip()
    label = "Ready For Review" if phase == "review" else "Complete"
    require(
        f"## Import Status: {label}" in response,
        f"Missing conversational status: {label}",
    )
    require("**Next Step:**" in response, "Incomplete final status block")
    require(
        response.rsplit("**Next Step:**", 1)[1].strip()
        and "\n\n" not in response.rsplit("**Next Step:**", 1)[1].strip(),
        "Text after final status block",
    )
    if phase == "review":
        require(
            all(Path(raw).stem in response.lower() for raw in SOURCES),
            "Review omits one statement",
        )
    runtime_check(evidence)


def correction_checks(root: Path) -> None:
    """The corrected inline fields are durable; a separate approval is still required."""
    status = load_state(inside(root, "statements/import-status.yml"))
    for raw, subject, value in (
        (SOURCES[0], "C-001", "Expenses:Food"),
        (SOURCES[1], "savings", "Assets:Savings"),
    ):
        doc = parsed_source(root, status_members(status)[raw]["parsed_group"], raw)
        decision = (
            transaction_decisions(doc).get(subject, {})
            if raw == SOURCES[0]
            else sole_account_review(doc)
        )
        require(
            decision.get("state") == "confirmed", "Missing resolved inline correction"
        )
        require("approval" not in doc["review"], "Correction was treated as approval")
        answer = decision.get("answer")
        # Answers preserve user wording. The structured fields below carry the
        # resolved account; do not require the prose to equal an account name.
        require(
            isinstance(answer, str) and bool(answer.strip()),
            "Missing inline human answer",
        )
        if raw == SOURCES[0]:
            require(
                any(p["account"] == value for p in decision["postings"]),
                "Wrong corrected transaction category",
            )
        else:
            require(decision.get("ledger_account") == value, "Wrong corrected mapping")


def scenario_checks(
    root: Path, evidence: Path, expected: dict[str, Any], phase: str
) -> None:
    status = source_checks(root, expected)
    sessions = list((root / ".auto-bean/import-sessions").glob("*.json"))
    require(len(sessions) == 1, "Exactly one import session is required")
    session = load_state(sessions[0])
    validate_state("session", root, session)
    session_status(session, status)
    require(
        {s["source_file"] for s in session_members(session)} == set(SOURCES),
        "Session mixing",
    )
    documents = {
        raw: parsed_source(root, item["parsed_group"], raw)
        for raw, item in status_members(status).items()
    }
    for raw, doc in documents.items():
        validate_state("parsed", root, doc)
        require(
            doc["source_file"] == raw
            and doc["source_fingerprint"] == "sha256:" + expected["sources"][raw]
            and doc["extraction_state"] == "complete",
            "Scenario source identity mismatch",
        )
        expected_rows = (
            [
                ("2026-01-05", Decimal(-25)),
                ("2026-01-10", Decimal(-100)),
                ("2026-01-15", Decimal(-5)),
            ]
            if raw == SOURCES[0]
            else [("2026-01-10", Decimal(100)), ("2026-01-31", Decimal(2))]
        )
        require(
            Counter(
                (r["transaction_date"], Decimal(r["amount"]))
                for r in doc["extracted_records"]
            )
            == Counter(expected_rows)
            and all(r["currency"] == "EUR" for r in doc["extracted_records"]),
            "Scenario source rows changed",
        )
        require("approval" not in doc["review"], "Fabricated or stale approval")
        review_validation(root, doc)
    memory_checks(root, session, documents, approved=False)
    require(
        financial_hashes(root) == expected["financial_hashes"],
        "Premature ledger writes",
    )
    if phase == "needs-input":
        mapping = sole_account_review(documents[SOURCES[1]])
        category = transaction_decisions(documents[SOURCES[0]]).get("C-001", {})
        require(
            mapping.get("state") == "needs_input" and mapping.get("suggestions"),
            "Missing unresolved account suggestions",
        )
        require(
            category.get("state") == "needs_input"
            and category.get("disposition") == "hold"
            and category.get("suggestions"),
            "Missing unresolved category suggestions",
        )
        label = "Needs Your Input"
    else:
        checkpoint = load_state(inside(evidence, "review.json"))
        require(
            checkpoint["session"]["groups"] == session["groups"],
            "Reviewed groups changed",
        )
        require(
            checkpoint["financial_hashes"] == expected["financial_hashes"],
            "Missing original review baseline",
        )
        expected_doc = copy.deepcopy(checkpoint["documents"][SOURCES[0]])
        transaction_decisions(expected_doc)["C-001"]["rationale"] = STALE_RATIONALE
        require(
            material_hash(documents[SOURCES[0]]) == material_hash(expected_doc)
            and material_hash(documents[SOURCES[0]])
            != checkpoint["review_digests"][SOURCES[0]],
            "Changed reviewed decision was lost or altered",
        )
        require(
            material_hash(documents[SOURCES[1]])
            == checkpoint["review_digests"][SOURCES[1]],
            "Unrelated reviewed statement changed",
        )
        require(
            all(
                item["current_status"] == "final_review"
                for item in status_members(status).values()
            ),
            "Stale review needs renewed approval",
        )
        label = "Ready For Review"
    response = inside(evidence, "last-response.txt").read_text()
    require(
        f"## Import Status: {label}" in response and "**Next Step:**" in response,
        "Missing conversational scenario status",
    )
    runtime_check(evidence)


STALE_RATIONALE = "Updated merchant interpretation requires renewed review."


def render_supporting_directives(root: Path, documents: dict[str, Any]) -> str:
    """Render independently checked proposals into beancount/reviewed.beancount."""
    lines = []
    for doc in documents.values():
        for entry in supporting_directives(root, doc):
            if isinstance(entry, Document):
                lines.append(
                    f"{entry.date} document {entry.account} "
                    + json.dumps("../" + doc["source_file"])
                )
            else:
                lines.append(f"{entry.date} balance {entry.account} {entry.amount}")
    return "\n".join(lines) + "\n"


def render_reviewed_transactions(documents: dict[str, Any]) -> str:
    """Trusted fixture renderer, independent of agent and product write code."""
    blocks = []
    for raw, doc in sorted(documents.items()):
        for row in doc["extracted_records"]:
            decision = row["review"]
            if (
                decision["disposition"] == "paired_transfer"
                and decision["posting_owner"] != raw
            ):
                continue
            require(
                decision["disposition"] in {"post", "paired_transfer"},
                "Unwritable reviewed row",
            )
            metadata = {
                "source": raw,
                "source_fingerprint": doc["source_fingerprint"],
                "account_id": row["account_id"],
                "record_id": row["record_id"],
            }
            for link in decision.get("linked_records", []):
                peer = documents[link["source_file"]]
                metadata.update(
                    peer_source=link["source_file"],
                    peer_source_fingerprint=peer["source_fingerprint"],
                    peer_account_id=link["account_id"],
                    peer_record_id=link["record_id"],
                )
            lines = [f"{row['transaction_date']} * {json.dumps(row['description'])}"]
            lines.extend(
                f"  {key}: {json.dumps(value)}" for key, value in metadata.items()
            )
            for posting in decision["postings"]:
                require(
                    not posting.get("cost") and not posting.get("price"),
                    "Fixture has no cost or price annotations",
                )
                lines.append(
                    f"  {posting['account']} {posting['amount']} {posting['currency']}"
                )
            blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "phase",
        choices=("init", "review", "correct", "approve", "needs-input", "stale"),
    )
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--plugin", type=Path, required=True)
    parser.add_argument("--expected", type=Path)
    parser.add_argument("--evidence", type=Path, default=Path("/opt/eval-evidence"))
    parser.add_argument("--logs", type=Path, default=Path("/logs/verifier"))
    parser.add_argument("--agent-logs", type=Path, default=Path("/logs/agent"))
    parser.add_argument(
        "--trace-policy",
        choices=("required", "state-only"),
        default=os.environ.get("AUTO_BEAN_TRACE_POLICY", "required"),
        help="state-only is an explicit verifier-side oracle/no-op control override",
    )
    args = parser.parse_args()
    if args.trace_policy not in {"required", "state-only"}:
        parser.error("Invalid AUTO_BEAN_TRACE_POLICY")
    report: dict[str, Any] = {"phase": args.phase, "passed": False}
    if args.phase != "init":
        write_review_html(args.ledger, args.logs / "review.html")
    state_checks: list[dict[str, Any]] = []
    token = _STATE_CHECKS.set(state_checks)
    try:
        if args.phase == "init":
            init_checks(args.ledger, args.plugin, args.evidence)
        else:
            require(args.expected is not None, "Expected baseline is required")
            if args.phase in {"needs-input", "stale"}:
                scenario_checks(
                    args.ledger,
                    args.evidence,
                    json.loads(args.expected.read_text()),
                    args.phase,
                )
            else:
                import_checks(
                    args.ledger,
                    args.plugin,
                    args.evidence,
                    json.loads(args.expected.read_text()),
                    "review" if args.phase == "correct" else args.phase,
                    explicit_group=args.phase == "review",
                )
                if args.phase == "correct":
                    correction_checks(args.ledger)
        report["passed"] = True
    except Exception as exc:
        report["failure"] = str(exc)
        if not state_checks or state_checks[-1]["status"] != "failed":
            frames = inspect.trace()
            location = frames[-1] if frames else None
            state_checks.append(
                {
                    "scope": "state",
                    "status": "error",
                    "requirement": "Evaluate state checks",
                    "detail": f"{type(exc).__name__}: {exc}",
                    "location": {
                        "file": location.filename if location else "unknown",
                        "function": location.function if location else "unknown",
                        "line": location.lineno if location else None,
                    },
                }
            )
            del frames, location
        state_checks.append(
            {
                "scope": "state",
                "status": "skipped",
                "requirement": "Remaining state checks",
                "detail": "State evaluation stopped at the preceding failure or error.",
            }
        )
    finally:
        _STATE_CHECKS.reset(token)
    report["state_passed"] = report["passed"]
    stage_groups: dict[str, list[dict[str, Any]]] = {}
    parsed_paths: list[str] = []
    if report["state_passed"] and args.phase != "init":
        session = load_state(
            next((args.ledger / ".auto-bean/import-sessions").glob("*.json"))
        )
        parsed_paths = [g["parsed_group"] for g in session["groups"]]
    if report["state_passed"] and args.phase in {"review", "needs-input", "correct"}:
        session = load_state(
            next((args.ledger / ".auto-bean/import-sessions").glob("*.json"))
        )
        members = {
            m["source_file"]: m["parsed_group"] for m in session_members(session)
        }
        for stage in (
            ["process", "categorize"] if args.phase != "correct" else ["categorize"]
        ):
            stage_groups[stage] = []
            for group in session["groups"]:
                paths = [
                    source if stage == "process" else members[source]
                    for source in group["source_files"]
                    if stage == "process"
                    or args.phase != "needs-input"
                    or any(
                        row.get("review")
                        for row in parsed_source(args.ledger, members[source], source)[
                            "extracted_records"
                        ]
                    )
                ]
                if paths:
                    stage_groups[stage].append(
                        {"group_id": group["group_id"], "paths": paths}
                    )
    trace = grade_trace(
        args.agent_logs,
        args.phase,
        stage_groups,
        parsed_paths,
        contents=snapshot_reader(args.ledger, args.plugin),
    )
    if not report["state_passed"] and args.phase != "init":
        state_checks.append(
            {
                "scope": "trace",
                "status": "skipped",
                "requirement": "State-dependent trace expectations",
                "detail": "Group worker and parsed-path expectations require valid state.",
            }
        )
    report["trace_passed"] = trace["passed"]
    report["trace_policy"] = args.trace_policy
    report["passed"] = report["state_passed"] and (
        report["trace_passed"] or args.trace_policy == "state-only"
    )
    if not trace["passed"] and args.trace_policy == "required":
        report.setdefault(
            "failure", "Plugin trace checks failed; see trace-report.json"
        )
    args.logs.mkdir(parents=True, exist_ok=True)
    finish_report(report, state_checks, trace)
    write_json(args.logs / "trace-report.json", trace)
    write_json(args.logs / "report.json", report)
    write_report_markdown(args.logs / "report.md", report)
    (args.logs / "reward.txt").write_text("1\n" if report["passed"] else "0\n")
    write_json(
        args.logs / "reward.json",
        {
            "reward": int(report["passed"]),
            "state": int(report["state_passed"]),
            "trace": int(report["trace_passed"]),
        },
    )
    print(json.dumps(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
