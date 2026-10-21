"""Oracle-only reference for parsed review and direct ledger writes; never included in agent images."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Any

import yaml

import json
from datetime import datetime, timezone

from evals.harbor.fixtures import SOURCES, sha256, write_json


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_state(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text()))


def session_path(root: Path) -> Path:
    return root / ".auto-bean/import-sessions" / f"{SESSION}.json"


def parsed_path(root: Path, source: str) -> Path:
    session = load_state(session_path(root))
    return root / next(
        str(g["parsed_group"]) for g in session["groups"] if source in g["source_files"]
    )


def read_statement(root: Path, source: str) -> dict[str, Any]:
    return next(
        d
        for d in load_state(parsed_path(root, source))["statements"]
        if d["source_file"] == source
    )


def save_statement(root: Path, source: str, data: dict[str, Any]) -> None:
    path = parsed_path(root, source)
    group = (
        load_state(path)
        if path.exists()
        else {"schema_version": 2, "group_id": "january", "statements": []}
    )
    group["statements"] = [
        d for d in group["statements"] if d["source_file"] != source
    ] + [data]
    write_json(path, group)


def account_decisions(doc: dict[str, Any]) -> dict[str, Any]:
    return {r["account_id"]: r["review"] for r in doc["statement_metadata"]["accounts"]}


def transaction_decisions(doc: dict[str, Any]) -> dict[str, Any]:
    return {r["record_id"]: r["review"] for r in doc["extracted_records"]}


def material(doc: dict[str, Any]) -> str:
    import hashlib

    result = {k: v for k, v in doc.items() if k != "review"}
    result["review"] = {
        "processing": {
            k: v
            for k, v in doc["review"]["processing"].items()
            if k in {"needs_input", "suggestions", "answer"}
        }
    }
    return hashlib.sha256(
        (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
    ).hexdigest()


ROWS = {
    "checking": [
        ("C-001", "2026-01-05", "Example Market", "-25.00"),
        ("XFER-001", "2026-01-10", "Transfer to own SAVINGS-TEST", "-100.00"),
        ("C-003", "2026-01-15", "Monthly bank fee", "-5.00"),
    ],
    "savings": [
        ("XFER-001", "2026-01-10", "From own CHECKING-TEST", "100.00"),
        ("S-002", "2026-01-31", "Savings interest", "2.00"),
    ],
}
SESSION = "harbor-import"


def draft(
    root: Path, plugin: Path, *, extract: bool = True, defer: bool = False
) -> None:
    fingerprints = {Path(raw).stem: "sha256:" + sha256(root / raw) for raw in SOURCES}
    status: dict[str, Any] = {
        "version": 1,
        "groups": {
            "january": {
                "session_id": SESSION,
                "current_status": "raw_ready",
                "parsed_group": "statements/parsed/january.json",
                "sources": {
                    raw: {"source_fingerprint": fingerprints[Path(raw).stem]}
                    for raw in SOURCES
                },
            }
        },
    }
    (root / "statements/import-status.yml").write_text(yaml.safe_dump(status))
    write_json(
        session_path(root),
        {
            "schema_version": 1,
            "session_id": SESSION,
            "created_at": now(),
            "groups": [
                {
                    "group_id": "january",
                    "name": "January accounts",
                    "origin": "agent" if defer else "user",
                    "source_files": list(SOURCES),
                    "parsed_group": "statements/parsed/january.json",
                }
            ],
            "price_runs": [],
        },
    )
    for raw in SOURCES:
        name = Path(raw).stem
        if extract:
            subprocess.run(
                [
                    "sh",
                    str(plugin / "runtime/launch.sh"),
                    "ensure-runtime",
                    "--workspace",
                    str(root),
                    "--extraction",
                ],
                check=True,
            )
            subprocess.run(
                [
                    "sh",
                    str(plugin / "runtime/launch.sh"),
                    "run",
                    "--workspace",
                    str(root),
                    "docling",
                    raw,
                    "--to",
                    "json",
                    "--output",
                    f".auto-bean/tmp/{name}",
                ],
                cwd=root,
                check=True,
                timeout=120,
            )
        data: dict[str, Any] = {
            "schema_version": 2,
            "source_file": raw,
            "source_fingerprint": fingerprints[name],
            "source_format": Path(raw).suffix[1:],
        }
        data.update(
            document_kind="statement",
            parse_run_id=f"oracle-{name}",
            parser={"name": "docling", "mode": "cli"},
            parsed_at=now(),
            extraction_state="complete",
        )
        data["statement_metadata"] = {
            "statement_period": {"start_date": "2026-01-01", "end_date": "2026-01-31"},
            "accounts": [
                {
                    "account_id": name,
                    "account_name": name.title(),
                    "primary_currency": "EUR",
                    "opening_balance": {
                        "date": "2026-01-01",
                        "amount": "1000.00" if name == "checking" else "500.00",
                        "currency": "EUR",
                    },
                    "closing_balance": {
                        "date": "2026-01-31",
                        "amount": "870.00" if name == "checking" else "602.00",
                        "currency": "EUR",
                    },
                }
            ],
        }
        data["extracted_records"] = [
            {
                "record_id": identifier,
                "source_reference": f"row:{i + 1}",
                "account_id": name,
                "transaction_date": day,
                "description": description,
                "amount": amount,
                "currency": "EUR",
            }
            for i, (identifier, day, description, amount) in enumerate(ROWS[name])
        ]
        review: dict[str, Any] = {}
        review["processing"] = {
            "attempts": 1,
            "outcome": "complete",
            "warnings": [],
            "evidence": [f"docling {raw} --to json; terminal exit 0"],
        }
        data["statement_metadata"]["accounts"][0]["review"] = {
            "state": "confirmed",
            "ledger_account": "Assets:" + name.title(),
            "rationale": "Explicit synthetic account identity",
            "reconciliation": [
                {
                    "date": "2026-02-01",
                    "currency": "EUR",
                    "ledger_amount": "870" if name == "checking" else "602",
                    "difference": "0",
                    "provenance": "Expected closing balance from source movements; canonical check follows writing",
                    "state": "matched",
                }
            ],
        }
        for row in data["extracted_records"]:
            record = row["record_id"]
            transfer = record == "XFER-001"
            contra = (
                "Assets:Savings"
                if transfer and name == "checking"
                else "Assets:Checking"
                if transfer
                else {
                    "C-001": "Expenses:Food",
                    "C-003": "Expenses:Bank-Fees",
                    "S-002": "Income:Interest",
                }[record]
            )
            from decimal import Decimal

            decision = {
                "state": "confirmed",
                "rationale": "Source row and explicit fixture account",
                "postings": [
                    {
                        "account": "Assets:" + name.title(),
                        "amount": row["amount"],
                        "currency": "EUR",
                    },
                    {
                        "account": contra,
                        "amount": str(-Decimal(row["amount"])),
                        "currency": "EUR",
                    },
                ],
                "findings": ["likely_transfer"] if transfer else [],
                "disposition": "paired_transfer" if transfer else "post",
                "linked_records": [
                    {
                        "source_file": SOURCES[1] if name == "checking" else SOURCES[0],
                        "account_id": "savings" if name == "checking" else "checking",
                        "record_id": record,
                    }
                ]
                if transfer
                else [],
            }
            if transfer:
                decision["posting_owner"] = SOURCES[0]
            row["review"] = decision
        data["review"] = review
        save_statement(root, raw, data)

    if defer:
        for raw, subject, kind in (
            (SOURCES[0], "C-001", "transaction"),
            (SOURCES[1], "savings", "account"),
        ):
            doc = read_statement(root, raw)
            if kind == "transaction":
                transaction_decisions(doc)[subject].update(
                    state="needs_input",
                    disposition="hold",
                    postings=[],
                    rationale="Which category for Example Market?",
                    suggestions=["Expenses:Food", "Expenses:Shopping"],
                )
            else:
                account_decisions(doc)[subject].pop("ledger_account", None)
                account_decisions(doc)[subject].update(
                    state="needs_input",
                    rationale="Which ledger account belongs to SAVINGS-TEST?",
                    suggestions=["Assets:Savings", "Assets:Checking"],
                )
            save_statement(root, raw, doc)
            status["groups"]["january"]["current_status"] = "account_blocked"
            status["groups"]["january"]["user_input_required"] = True
        (root / "statements/import-status.yml").write_text(yaml.safe_dump(status))
    else:
        stage(root)


def stage(root: Path) -> None:
    """Review is the current parsed postings; canonical files remain untouched."""
    status = yaml.safe_load((root / "statements/import-status.yml").read_text())
    for item in status["groups"].values():
        item["current_status"] = "final_review"
        item["user_input_required"] = False
    (root / "statements/import-status.yml").write_text(yaml.safe_dump(status))


def write_reviewed(root: Path) -> None:
    """Reference Write step edits canonical files from reviewed rows exactly once."""
    docs = {raw: read_statement(root, raw) for raw in SOURCES}
    blocks = []
    for raw, doc in docs.items():
        for row in doc["extracted_records"]:
            decision = row["review"]
            if (
                decision["disposition"] == "paired_transfer"
                and decision["posting_owner"] != raw
            ):
                continue
            assert (
                decision["state"] != "needs_input" and decision["disposition"] != "hold"
            )
            lines = [f"{row['transaction_date']} * {json.dumps(row['description'])}"]
            metadata = {
                "source": raw,
                "source_fingerprint": doc["source_fingerprint"],
                "account_id": row["account_id"],
                "record_id": row["record_id"],
            }
            for link in decision.get("linked_records", []):
                metadata.update(
                    peer_source=link["source_file"],
                    peer_source_fingerprint=docs[link["source_file"]][
                        "source_fingerprint"
                    ],
                    peer_account_id=link["account_id"],
                    peer_record_id=link["record_id"],
                )
            lines.extend(
                f"  {key}: {json.dumps(value)}" for key, value in metadata.items()
            )
            lines.extend(
                f"  {p['account']} {p['amount']} {p['currency']}"
                for p in decision["postings"]
            )
            blocks.append("\n".join(lines))
    content = "\n\n".join(blocks) + "\n"
    target = root / "beancount/imports.beancount"
    if target.exists():
        assert target.read_text() == content, (
            "Existing import differs; manual repair required"
        )
    else:
        target.write_text(content)
    ledger = root / "ledger.beancount"
    include = 'include "beancount/imports.beancount"'
    if include not in ledger.read_text():
        ledger.write_text(ledger.read_text() + "\n" + include + "\n")


def approve(root: Path, checkpoint_path: Path) -> None:
    """Called only for the harness's explicit chat approval step."""
    from auto_bean.reconciliation import validate_import

    checkpoint = load_state(checkpoint_path)
    for raw in SOURCES:
        doc = read_statement(root, raw)
        assert material(doc) == checkpoint["review_digests"][raw], (
            "Reviewed decisions changed; renewed approval required"
        )
    write_reviewed(root)
    session = load_state(session_path(root))
    session["price_runs"] = [
        {
            "run_id": "eur-no-op",
            "requested_date": "2026-02-01",
            "state": "no_op",
            "required_commodities": [],
            "coverage": [],
            "preflight": "passed",
            "preflight_job_count": 0,
            "execution": {
                "state": "complete",
                "exit_code": 0,
                "duration_seconds": 0,
                "stderr_summary": "",
            },
            "jobs": [],
            "detail": "EUR only; zero quote jobs and no price changes.",
        }
    ]
    write_json(session_path(root), session)
    result = validate_import(root, SESSION, stage="written")
    assert result["state"] == "passed", result
    status = yaml.safe_load((root / "statements/import-status.yml").read_text())
    for item in status["groups"].values():
        item["current_status"] = "done"
    (root / "statements/import-status.yml").write_text(yaml.safe_dump(status))
    remember_applied_decisions(root)


def remember_applied_decisions(root: Path) -> None:
    """Persist real narrowly scoped records after the oracle's approved write."""
    session = load_state(session_path(root))
    timestamp = now()
    for raw in SOURCES:
        name = Path(raw).stem
        doc = read_statement(root, raw)
        scope = {
            "account_names": [name.upper() + "-TEST"],
            "account_owner": "Alex Example",
            "currency": "EUR",
        }
        common = {
            "schema_version": 1,
            "source": {
                "statement_source": parsed_path(root, raw).relative_to(root).as_posix(),
                "source_fingerprint": doc["source_fingerprint"],
            },
            "scope": scope,
            "review_state": "approved",
            "created_at": timestamp,
            "updated_at": timestamp,
            "audit": {
                "originating_workflow": "auto-bean-import",
                "session_id": session["session_id"],
                "review_digest": material(doc),
                "validated_at": doc["review"]["validation"]["checked_at"],
            },
        }
        records = [
            (
                "account_mappings.json",
                {
                    **common,
                    "record_id": "account-" + name,
                    "memory_type": "account_mapping",
                    "decision": {
                        "external_account_label": name.upper() + "-TEST",
                        "beancount_account": account_decisions(doc)[name][
                            "ledger_account"
                        ],
                    },
                },
            )
        ]
        if name == "checking":
            records.append(
                (
                    "category_mappings.json",
                    {
                        **common,
                        "record_id": "category-example-market-checking",
                        "memory_type": "category_mapping",
                        "decision": {
                            "match": {"payee_contains": "Example Market"},
                            "posting_account": next(
                                p["account"]
                                for p in transaction_decisions(doc)["C-001"]["postings"]
                                if p["account"].startswith("Expenses:")
                            ),
                        },
                    },
                )
            )
        for filename, record in records:
            path = root / ".auto-bean/memory" / filename
            data = load_state(path)
            if not any(r["record_id"] == record["record_id"] for r in data["records"]):
                data["records"].append(record)
                write_json(path, data)


def correct(root: Path) -> None:
    checking = read_statement(root, SOURCES[0])
    transaction_decisions(checking)["C-001"].update(
        answer="Expenses:Food",
        disposition="post",
        state="confirmed",
        postings=[
            {"account": "Assets:Checking", "amount": "-25", "currency": "EUR"},
            {"account": "Expenses:Food", "amount": "25", "currency": "EUR"},
        ],
    )
    save_statement(root, SOURCES[0], checking)
    savings = read_statement(root, SOURCES[1])
    account_decisions(savings)["savings"].update(
        answer="Assets:Savings", ledger_account="Assets:Savings", state="confirmed"
    )
    save_statement(root, SOURCES[1], savings)
    stage(root)


def stale(root: Path, checkpoint_path: Path | None = None) -> None:
    checkpoint = load_state(checkpoint_path or Path("/opt/eval-evidence/review.json"))
    doc = read_statement(root, SOURCES[0])
    assert material(doc) != checkpoint["review_digests"][SOURCES[0]], (
        "Expected changed review evidence"
    )
    # Current user instruction explicitly withholds approval when evidence changed.
    # Preserve the edit and return for review; do not create an approval artifact.
    stage(root)


def main() -> None:
    from evals.harbor.capture import capture

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "phase", choices=("review", "approve", "needs-input", "correct", "stale")
    )
    args = parser.parse_args()
    root = Path("/app/ledger")
    plugin = Path("/opt/auto-bean-marketplace/plugins/auto-bean")
    evidence = Path("/opt/eval-evidence")
    if args.phase in {"review", "needs-input"}:
        draft(root, plugin, defer=args.phase == "needs-input")
    elif args.phase == "correct":
        correct(root)
    elif args.phase == "stale":
        stale(root)
    else:
        approve(root, evidence / "review.json")
    capture(root, plugin, evidence, args.phase)
    label = (
        "Needs Your Input"
        if args.phase == "needs-input"
        else "Complete"
        if args.phase == "approve"
        else "Ready For Review"
    )
    (evidence / "last-response.txt").write_text(
        f"checking.csv and savings.pdf: four transactions, one paired transfer.\n\n---\n\n## Import Status: {label}\n\n**Summary:** Both statements reconciled.\n**Next Step:** "
        + (
            "Approve the reviewed transactions.\n"
            if args.phase == "review"
            else "None.\n"
        )
    )


if __name__ == "__main__":
    main()
