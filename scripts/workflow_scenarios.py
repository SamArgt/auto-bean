"""Prepare isolated synthetic ledgers and verify observable agent workflow outcomes."""

from __future__ import annotations

import argparse
import csv
from decimal import Decimal
import hashlib
import io
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/auto-bean"
SCENARIOS = (
    "paired-transfer",
    "overlapping-export",
    "resume-write",
    "reject-dirty",
    "malformed-multi-account",
    "partial-price-failure",
)


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def transaction(
    amount: str, record: str, fingerprint: str, *, account: str = "Expenses:Food"
) -> str:
    return f'\n2026-01-10 * "Example Shop" "Fixture purchase"\n  source: "statements/raw/checking.csv"\n  source_fingerprint: "{fingerprint}"\n  account_id: "checking"\n  record_id: "{record}"\n  Assets:Checking -{amount} EUR\n  {account} {amount} EUR\n'


def prepare(destination: Path) -> list[Path]:
    if destination.exists():
        raise ValueError(
            "Choose a new destination; existing evaluations are never overwritten."
        )
    ledgers = []
    for name in SCENARIOS:
        folder = destination / name
        ledger = folder / "ledger"
        shutil.copytree(PLUGIN / "assets/workspace_template", ledger)
        dump(ledger / ".auto-bean/workspace.json", {"format_version": 1})
        (ledger / ".gitignore").write_text(
            ".auto-bean/runtime/\n.auto-bean/tmp/\n.auto-bean/migrations/\n"
        )
        (ledger / "statements/raw").mkdir(exist_ok=True)
        (ledger / "statements/parsed").mkdir(exist_ok=True)
        (ledger / "beancount/accounts.beancount").write_text(
            "1970-01-01 open Assets:Checking EUR\n1970-01-01 open Assets:Savings EUR\n1970-01-01 open Expenses:Food EUR\n1970-01-01 open Equity:Opening-Balances EUR\n"
        )
        (ledger / "beancount/opening-balances.beancount").write_text(
            '2025-12-31 * "Opening" "Existing balance"\n  Assets:Checking 200 EUR\n  Equity:Opening-Balances -200 EUR\n'
        )
        entries: dict[str, Any] = {}
        for account, amount in (
            (("checking", "-100.00"), ("savings", "100.00"))
            if name == "paired-transfer"
            else (("checking", "-25.00"),)
        ):
            raw = f"statements/raw/{account}.csv"
            (ledger / raw).write_text(
                f"Date,Description,Amount,Currency\n2026-01-10,{'Own account transfer' if name == 'paired-transfer' else 'Example Shop'},{amount},EUR\n"
            )
            if name == "overlapping-export":
                with (ledger / raw).open("a") as stream:
                    stream.write("2026-01-12,Example Shop,-20.00,EUR\n")
            fingerprint = (
                "sha256:" + hashlib.sha256((ledger / raw).read_bytes()).hexdigest()
            )
            parsed = json.loads(
                (PLUGIN / "references/parsed-statement-output.example.json").read_text()
            )
            parsed.update(
                source_file=raw,
                source_fingerprint=fingerprint,
                source_format="csv",
                parse_run_id=f"fixture-{account}",
                process_artifact=f".auto-bean/artifacts/process/{account}--process.md",
            )
            parsed["statement_metadata"]["accounts"] = [
                {
                    "account_id": account,
                    "account_name": "Own " + account,
                    "primary_currency": "EUR",
                }
            ]
            if name == "paired-transfer":
                parsed_account = parsed["statement_metadata"]["accounts"][0]
                parsed_account["opening_balance"] = {
                    "date": "2026-01-01",
                    "amount": "200.00" if account == "checking" else "0.00",
                    "currency": "EUR",
                }
                parsed_account["closing_balance"] = {
                    "date": "2026-01-31",
                    "amount": "100.00",
                    "currency": "EUR",
                }
            record = {
                "record_id": "bank-row-1",
                "source_reference": "row:2",
                "account_id": account,
                "transaction_date": "2026-01-10",
                "description": "Own account transfer"
                if name == "paired-transfer"
                else "Example Shop",
                "payee": "Example Shop",
                "amount": amount,
                "currency": "EUR",
            }
            parsed["extracted_records"] = [record]
            paths = {
                stage: f".auto-bean/artifacts/{stage}/{account}--{stage}.md"
                for stage in ("process", "categorize", "import")
            }
            for stage, relative in paths.items():
                target = ledger / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(
                    f"# {stage.title()} fixture {account}\n\nSource: {raw}\nFingerprint: {fingerprint}\nParsed: statements/parsed/{account}.json\nAccount identity and EUR currency are confirmed by the owner. Ledger account: Assets:{account.title()}.\nNo pending source questions. Source-row identity: bank-row-1.\n"
                )
            entries[raw] = {
                "current_status": "categorize_ready",
                "source_fingerprint": fingerprint,
                "parsed_statement": f"statements/parsed/{account}.json",
                "artifacts": paths,
            }
            if name != "paired-transfer":
                parsed["document_kind"] = "transaction_export"
                parsed["statement_metadata"].pop("statement_period", None)
            if name == "malformed-multi-account":
                parsed["statement_metadata"]["accounts"].append(
                    dict(parsed["statement_metadata"]["accounts"][0])
                )
            if name in {"resume-write", "reject-dirty", "overlapping-export"}:
                entry = entries[raw]
                entry["current_status"] = (
                    "final_review"
                    if name == "reject-dirty"
                    else "write_blocked"
                    if name == "resume-write"
                    else "write_ready"
                )
                amount = "10" if name == "reject-dirty" else "25"
                with (ledger / "ledger.beancount").open("a") as stream:
                    stream.write(transaction(amount, "bank-row-1", fingerprint))
                (ledger / paths["categorize"]).write_text(
                    f"# Reviewed categorization\nParsed: statements/parsed/{account}.json\nDisposition: post; bank-row-1, 2026-01-10, Example Shop, Assets:Checking -25 EUR, Expenses:Food 25 EUR. Account/category facts are supplied by the owner.\n"
                )
                with (ledger / paths["import"]).open("a") as stream:
                    stream.write(
                        "\n## Posting Decisions\nA candidate for bank-row-1 already exists in ledger.beancount; writing was interrupted after append, before final validation/approval. No final approval was obtained.\n"
                    )
                if name == "overlapping-export":
                    parsed["extracted_records"].append(
                        {
                            **record,
                            "record_id": "bank-row-2",
                            "source_reference": "row:3",
                            "amount": "-20.00",
                            "transaction_date": "2026-01-12",
                        }
                    )
                    with (ledger / paths["categorize"]).open("a") as stream:
                        stream.write(
                            "bank-row-1: existing_duplicate, exact provenance match to the existing transaction; bank-row-2: post, 2026-01-12, Example Shop, Assets:Checking -20 EUR, Expenses:Food 20 EUR.\n"
                        )
            dump(ledger / f"statements/parsed/{account}.json", parsed)
            with (ledger / "ledger.beancount").open("a") as stream:
                stream.write(
                    f'\n2026-01-31 document Assets:{account.title()} "{raw}"\n'
                )
        (ledger / "statements/import-status.yml").write_text(
            yaml.safe_dump({"version": 1, "statements": entries}, sort_keys=False)
        )
        notes = ledger / "personal-notes.txt"
        notes.write_text("User notes: preserve this file.\n")
        env = dict(
            os.environ,
            GIT_CONFIG_NOSYSTEM="1",
            GIT_CONFIG_GLOBAL="/dev/null",
            GIT_AUTHOR_NAME="Workflow Fixture",
            GIT_AUTHOR_EMAIL="fixture@example.test",
            GIT_COMMITTER_NAME="Workflow Fixture",
            GIT_COMMITTER_EMAIL="fixture@example.test",
        )
        for command in (
            ["git", "init"],
            ["git", "add", "--all"],
            ["git", "commit", "-m", "Synthetic workflow fixture"],
        ):
            subprocess.run(
                command, cwd=ledger, env=env, check=True, capture_output=True
            )
        if name == "reject-dirty":
            notes.write_text("User notes: staged edit must survive.\n")
            subprocess.run(["git", "add", "personal-notes.txt"], cwd=ledger, check=True)
            notes.write_text(
                "User notes: staged edit must survive.\nAdditional unstaged note.\n"
            )
        requests = {
            "paired-transfer": "Import these two parsed statements. Checking and Savings are both my own accounts; their opposite EUR 100 rows are one transfer. Continue through the validated ledger draft and show it for final review. I have not approved the final result.",
            "overlapping-export": "Continue this import. The existing bank-row-1 entry is the same purchase as this export's row; keep it once. The additional bank-row-2 purchase is food for EUR 20. Draft that remaining entry and present final review; I have not approved it.",
            "resume-write": "Resume this interrupted statement write. The EUR 25 Example Shop purchase belongs to Expenses:Food. Inspect the existing candidate, finish validation, and present final review; I have not approved it.",
            "reject-dirty": "I reject the EUR 10 candidate identified by bank-row-1. Remove that candidate only and keep my staged and unstaged personal notes. I do not approve this statement. Record the blocked/rejected outcome without committing anything.",
            "malformed-multi-account": "Continue importing the supplied parsed statement. Preserve source evidence and report any repair needed before posting. Do not guess account identity.",
            "partial-price-failure": "Use the prices skill to review my captured fetch result in .auto-bean/tmp/price-transcript.json. Do not fetch again or write prices. Explain whether the run completed successfully, persist the price-stage outcome, and keep statement status unchanged.",
        }
        if name == "partial-price-failure":
            dump(
                ledger / ".auto-bean/tmp/price-transcript.json",
                {
                    "mode": "snapshot",
                    "date": "2026-01-10",
                    "dry_run_jobs": 2,
                    "terminal_exit_code": 0,
                    "stdout": "2026-01-10 price AAPL 250 USD",
                    "stderr": "ERROR: second provider failed; no quote",
                    "duration_seconds": 3,
                },
            )
        skill = (
            "auto-bean-prices"
            if name == "partial-price-failure"
            else "auto-bean-import"
        )
        (folder / "request.txt").write_text(
            f"Use the skill at {PLUGIN / 'skills' / skill / 'SKILL.md'} in the ledger at {ledger}.\n\n{requests[name]}\n\nAll data is synthetic. Do not commit or push. Only write inside this ledger; do not edit the product repository or fixtures outside it.\n"
        )
        dump(
            folder / "expected.json",
            {
                "transaction_count": {
                    "paired-transfer": 1,
                    "overlapping-export": 2,
                    "resume-write": 1,
                    "reject-dirty": 0,
                    "malformed-multi-account": 0,
                    "partial-price-failure": 0,
                }[name],
                "notes": notes.read_text(),
                "staged_notes": subprocess.check_output(
                    ["git", "show", ":personal-notes.txt"], cwd=ledger, text=True
                ),
                "prices": (ledger / "beancount/prices.beancount").read_text(),
                "head": subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=ledger, text=True
                ),
                "status_before": (ledger / "statements/import-status.yml").read_text(),
            },
        )
        ledgers.append(ledger)
    return ledgers


def verify(ledger: Path) -> None:
    expected = json.loads((ledger.parent / "expected.json").read_text())
    launch = [
        "sh",
        str(PLUGIN / "runtime/launch.sh"),
        "run",
        "--workspace",
        str(ledger),
    ]
    subprocess.run(
        [*launch, "bean-check", "ledger.beancount"],
        check=True,
        capture_output=True,
        text=True,
    )
    # BQL rows are postings; count economic transactions with the actual loader.
    output = subprocess.check_output(
        [
            *launch,
            "python",
            "-c",
            "from beancount import loader; from beancount.core.data import Transaction; "
            "from datetime import date; entries, errors, _ = loader.load_file('ledger.beancount'); "
            "assert not errors; print(sum(isinstance(e, Transaction) and "
            "date(2026, 1, 1) <= e.date < date(2026, 2, 1) for e in entries))",
        ],
        text=True,
    )
    assert int(output.strip()) == expected["transaction_count"], output
    balances = subprocess.check_output(
        [
            *launch,
            "bean-query",
            "--format",
            "csv",
            "ledger.beancount",
            "SELECT account, sum(number) AS amount WHERE account ~ '^Assets:(Checking|Savings)$' GROUP BY account;",
        ],
        text=True,
    )
    amounts = {
        row["account"]: Decimal(row["amount"])
        for row in csv.DictReader(io.StringIO(balances))
    }
    checking = {
        "paired-transfer": "100",
        "overlapping-export": "155",
        "resume-write": "175",
    }.get(ledger.parent.name, "200")
    assert amounts.get("Assets:Checking", Decimal(0)) == Decimal(checking), balances
    if ledger.parent.name == "paired-transfer":
        assert amounts.get("Assets:Savings", Decimal(0)) == Decimal("100"), balances
    assert (ledger / "personal-notes.txt").read_text() == expected["notes"]
    assert (
        subprocess.check_output(
            ["git", "show", ":personal-notes.txt"], cwd=ledger, text=True
        )
        == expected["staged_notes"]
    )
    assert (
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ledger, text=True)
        == expected["head"]
    )
    assert (ledger / "beancount/prices.beancount").read_text() == expected["prices"]
    states = yaml.safe_load((ledger / "statements/import-status.yml").read_text())[
        "statements"
    ]
    assert all(entry["current_status"] != "done" for entry in states.values()), (
        "No final approval was given"
    )
    name = ledger.parent.name
    if name in {"paired-transfer", "overlapping-export", "resume-write"}:
        assert all(
            entry["current_status"] == "final_review" for entry in states.values()
        )
    if name in {"reject-dirty", "malformed-multi-account"}:
        assert all(
            entry["current_status"].endswith("_blocked") for entry in states.values()
        )
    if name == "partial-price-failure":
        assert (ledger / "statements/import-status.yml").read_text() == expected[
            "status_before"
        ]
        assert list((ledger / ".auto-bean/artifacts/prices").glob("*.md")), (
            "Missing price outcome"
        )
    print(
        f"{name}: observable ledger, review status, user changes, and history checks passed."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "verify"))
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    if args.action == "prepare":
        for ledger in prepare(args.path.expanduser().absolute()):
            print(ledger.parent / "request.txt")
    else:
        verify(args.path.expanduser().resolve())


if __name__ == "__main__":
    main()
