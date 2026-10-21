"""Trusted semantic graders. No agent code or workspace Python is imported."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from beancount import loader
from beancount.core.data import Open, Transaction

# These imports resolve to the verifier's immutable bundle, never the ledger.
from auto_bean.validation import load_state, validate_state
from evals.harbor.fixtures import OPENING, SOURCES, sha256, write_json

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


def require(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


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
    for path in root.rglob("*.beancount"):
        require(not path.is_symlink(), "Ledger contains a symlink")
        for line in path.read_text().splitlines():
            require(
                not re.match(r"\s*plugin\s", line),
                "Unexpected executable ledger plugin",
            )
            match = re.match(r'\s*include\s+"([^"]+)"', line)
            if match:
                target = path.parent / match[1]
                require(
                    target.resolve().is_relative_to(root.resolve()),
                    "Include escapes ledger",
                )
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
        set(status["statements"]) == set(SOURCES),
        "Status must describe exactly the two raw statements",
    )
    return status


def import_checks(
    root: Path, plugin: Path, evidence: Path, expected: dict[str, Any], phase: str
) -> None:
    del plugin  # The validator imports the immutable verifier bundle.
    status = source_checks(root, expected)
    wanted = "final_review" if phase == "review" else "done"
    require(
        all(item["current_status"] == wanted for item in status["statements"].values()),
        f"Both statements must be {wanted}",
    )
    entries, _ = load_ledger(root)
    transactions = [entry for entry in entries if isinstance(entry, Transaction)]
    opening = [entry for entry in transactions if entry.date == date(2025, 12, 31)]
    require(
        len(opening) == 1
        and (root / "beancount/opening-balances.beancount").read_text() == OPENING,
        "Existing opening transaction was changed",
    )
    current = [entry for entry in transactions if entry not in opening]
    expected_keys = Counter(
        (
            day,
            tuple(
                (account, Decimal(amount), currency)
                for account, amount, currency in sorted(postings)
            ),
        )
        for day, postings in EXPECTED_POSTINGS
    )
    require(
        Counter(economic_key(entry) for entry in current) == expected_keys,
        "Wrong economic transactions, dates, accounts, amounts, or duplicate transfer",
    )
    require(all(entry.flag == "*" for entry in current), "Unexpected transaction flags")
    balances: dict[str, Decimal] = defaultdict(Decimal)
    for entry in transactions:
        for posting in entry.postings:
            units = posting.units
            assert units is not None and isinstance(units.number, Decimal)
            if units.currency == "EUR":
                balances[posting.account] += units.number
    require(
        balances["Assets:Checking"] == Decimal(870)
        and balances["Assets:Savings"] == Decimal(602),
        "Closing balances do not reconcile",
    )
    all_artifacts = []
    for raw, item in status["statements"].items():
        fingerprint = "sha256:" + expected["sources"][raw]
        require(
            item["source_fingerprint"] == fingerprint,
            "Status fingerprint disagrees with raw evidence",
        )
        parsed = load_state(inside(root, item["parsed_statement"]))
        validate_state("parsed", root, parsed)
        require(
            parsed.get("schema_version") == 1
            and parsed["document_kind"] == "statement",
            "Expected new normalized statement schema",
        )
        require(
            parsed["source_file"] == raw
            and parsed["source_fingerprint"] == fingerprint,
            "Parsed source identity mismatch",
        )
        accounts = parsed["statement_metadata"]["accounts"]
        require(len(accounts) == 1, "Each fixture has exactly one account")
        checking = raw.endswith("checking.csv")
        account = accounts[0]
        require(account["primary_currency"] == "EUR", "Wrong statement currency")
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
            Counter(
                (row["transaction_date"], Decimal(row["amount"])) for row in records
            )
            == Counter(expected_rows),
            "Raw statement rows were lost, invented, or changed",
        )
        for record in records:
            candidates = [
                entry
                for entry in current
                if entry.date.isoformat() == record["transaction_date"]
            ]
            require(
                len(candidates) == 1,
                "Cannot locate source record's economic transaction",
            )
            # The write skill permits each bank posting to carry its own
            # provenance, as well as transaction-level companion metadata.
            metadata = json.dumps(
                {
                    "transaction": candidates[0].meta,
                    "postings": [posting.meta for posting in candidates[0].postings],
                },
                default=str,
            )
            require(
                all(
                    value in metadata
                    for value in (
                        fingerprint,
                        record["account_id"],
                        record["record_id"],
                    )
                ),
                "Transaction lacks full source-record provenance (including the shared transfer)",
            )
        require(
            set(item["artifacts"]) == {"process", "categorize", "import"},
            "Missing stage artifact pointers",
        )
        for stage, relative in item["artifacts"].items():
            text = inside(root, relative).read_text()
            require(text.strip(), f"Empty {stage} artifact")
            if stage == "process":
                require(
                    "docling" in text.lower(), "No real extraction command recorded"
                )
                require(
                    parsed["process_artifact"] == relative,
                    "Process artifact pointers disagree",
                )
            if stage == "import":
                require(
                    "Posting Decisions" in text and "Cross-Statement Review" in text,
                    "Missing import decisions",
                )
                if phase == "approve":
                    clean = re.sub(r"[*`]", "", text)
                    require(
                        bool(
                            re.search(
                                r"\bI approve\b|\b(?:user|owner)\s+(?:explicitly\s+)?approved\b|\b(?:user|explicit|final) approval\s*[:=-]\s*(?:approved|received|granted|accepted)",
                                clean,
                                re.I,
                            )
                        ),
                        "Missing explicit user approval evidence",
                    )
                all_artifacts.append(text)
    artifacts_text = "\n".join(all_artifacts)
    # Bind the actual changed financial files to the recorded candidate hashes.
    changed = git(root, "diff", "--name-only").splitlines()
    changed += git(root, "ls-files", "--others", "--exclude-standard").splitlines()
    for relative in set(changed):
        if relative.endswith(".beancount"):
            require(
                sha256(inside(root, relative)) in artifacts_text,
                f"Missing candidate hash: {relative}",
            )
    if phase == "approve":
        price_files = list((root / ".auto-bean/artifacts/prices").glob("*.md"))
        require(
            any(path.read_text().strip() for path in price_files),
            "Missing prices stage outcome",
        )
        memory_files = list((root / ".auto-bean/artifacts/memory").glob("*.md"))
        # Memory's normal handoff belongs in import's existing artifact; no
        # extra product output schema or directory is required.
        require(
            any(path.read_text().strip() for path in memory_files)
            or all(
                section_content(text, "Memory Attribution")
                and section_content(text, "Memory Candidates")
                for text in all_artifacts
            ),
            "Missing memory handoff outcome in the import artifacts",
        )
    for path in (root / ".auto-bean/memory").rglob("*.json"):
        validate_state("memory", root, load_state(path))
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
    else:
        checkpoint = json.loads(inside(evidence, "review.json").read_text())
        previous = __import__("yaml").safe_load(checkpoint["status"])
        require(
            all(
                item["current_status"] == "final_review"
                for item in previous["statements"].values()
            ),
            "Approval lacks a preceding review checkpoint",
        )
        current_hashes = {
            path.relative_to(root).as_posix(): sha256(path)
            for path in root.rglob("*.beancount")
            if ".auto-bean" not in path.relative_to(root).parts
        }
        require(
            current_hashes == checkpoint["financial_hashes"],
            "Approval changed the reviewed financial candidate",
        )
    runtime_check(evidence)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("init", "review", "approve"))
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--plugin", type=Path, required=True)
    parser.add_argument("--expected", type=Path)
    parser.add_argument("--evidence", type=Path, default=Path("/opt/eval-evidence"))
    parser.add_argument("--logs", type=Path, default=Path("/logs/verifier"))
    args = parser.parse_args()
    report: dict[str, Any] = {"phase": args.phase, "passed": False}
    try:
        if args.phase == "init":
            init_checks(args.ledger, args.plugin, args.evidence)
        else:
            require(args.expected is not None, "Expected baseline is required")
            import_checks(
                args.ledger,
                args.plugin,
                args.evidence,
                json.loads(args.expected.read_text()),
                args.phase,
            )
        report["passed"] = True
    except Exception as exc:
        report["failure"] = str(exc)
    args.logs.mkdir(parents=True, exist_ok=True)
    write_json(args.logs / "report.json", report)
    (args.logs / "reward.txt").write_text("1\n" if report["passed"] else "0\n")
    print(json.dumps(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
