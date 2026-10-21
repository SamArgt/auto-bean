"""Oracle-only solution. Uploaded by Harbor after the agent environment starts."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from evals.harbor.fixtures import SOURCES, sha256, write_json

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


def draft(root: Path, plugin: Path, *, extract: bool = True) -> None:
    import yaml

    status: dict[str, Any] = {"version": 1, "statements": {}}
    fingerprints = {Path(raw).stem: "sha256:" + sha256(root / raw) for raw in SOURCES}
    for raw in SOURCES:
        name = Path(raw).stem
        artifacts = {
            stage: f".auto-bean/artifacts/{stage}/{name}--{stage}.md"
            for stage in ("process", "categorize", "import")
        }
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
        parsed = {
            "schema_version": 1,
            "document_kind": "statement",
            "parse_run_id": f"oracle-{name}",
            "source_file": raw,
            "source_fingerprint": fingerprints[name],
            "source_format": Path(raw).suffix[1:],
            "parser": {"name": "docling", "mode": "cli"},
            "parsed_at": "2026-02-01T00:00:00Z",
            "process_artifact": artifacts["process"],
            "statement_metadata": {
                "statement_period": {
                    "start_date": "2026-01-01",
                    "end_date": "2026-01-31",
                },
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
            },
            "extracted_records": [
                {
                    "record_id": identifier,
                    "source_reference": f"row:{index + 1}",
                    "account_id": name,
                    "transaction_date": day,
                    "description": description,
                    "amount": amount,
                    "currency": "EUR",
                }
                for index, (identifier, day, description, amount) in enumerate(
                    ROWS[name]
                )
            ],
        }
        write_json(root / f"statements/parsed/{name}.json", parsed)
        status["statements"][raw] = {
            "current_status": "final_review",
            "source_fingerprint": fingerprints[name],
            "parsed_statement": f"statements/parsed/{name}.json",
            "artifacts": artifacts,
        }
        for stage, relative in artifacts.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                f"# {stage.title()} Decisions {name}\nSource: {raw}\nFingerprint: {fingerprints[name]}\n\n"
            )
        (root / artifacts["process"]).write_text(
            f"# Process Decisions {name}\ndocling {raw} --to json --output .auto-bean/tmp/{name}\nTerminal exit: 0. Attempts: 1.\nAccount identity and all source rows confirmed.\n"
        )
    target = root / "beancount/imports.beancount"

    def transaction(
        day: str,
        description: str,
        account: str,
        record: str,
        postings: str,
        other: bool = False,
    ) -> str:
        metadata = f'  source_fingerprint: "{fingerprints[account]}"\n  account_id: "{account}"\n  record_id: "{record}"\n'
        if other:
            metadata += f'  paired_source_fingerprint: "{fingerprints["savings"]}"\n  paired_account_id: "savings"\n  paired_record_id: "XFER-001"\n'
        return f'2026-{day} * "{description}"\n{metadata}{postings}\n'

    target.write_text(
        transaction(
            "01-05",
            "Example Market",
            "checking",
            "C-001",
            "  Assets:Checking -25 EUR\n  Expenses:Food 25 EUR\n",
        )
        + transaction(
            "01-10",
            "Own account transfer",
            "checking",
            "XFER-001",
            "  Assets:Checking -100 EUR\n  Assets:Savings 100 EUR\n",
            True,
        )
        + transaction(
            "01-15",
            "Monthly bank fee",
            "checking",
            "C-003",
            "  Assets:Checking -5 EUR\n  Expenses:Bank-Fees 5 EUR\n",
        )
        + transaction(
            "01-31",
            "Savings interest",
            "savings",
            "S-002",
            "  Assets:Savings 2 EUR\n  Income:Interest -2 EUR\n",
        )
    )
    with (root / "ledger.beancount").open("a") as stream:
        stream.write('\ninclude "beancount/imports.beancount"\n')
    hashes = "\n".join(
        f"{relative}: {sha256(root / relative)}"
        for relative in ("ledger.beancount", "beancount/imports.beancount")
    )
    for item in status["statements"].values():
        with (root / item["artifacts"]["import"]).open("a") as stream:
            stream.write(
                f"## Cross-Statement Review\nXFER-001 is one paired transfer, posting owner checking; both source records retained.\n\n## Posting Decisions\nValidated with bean-check. Closing balances checking 870 EUR; savings 602 EUR.\nCandidate after hashes:\n{hashes}\nFinal approval is pending.\n"
            )
    (root / "statements/import-status.yml").write_text(
        yaml.safe_dump(status, sort_keys=False)
    )
    for stage, text in (
        (
            "prices",
            "EUR only: no quote jobs, no emitted prices, terminal exit 0, no follow-up.",
        ),
        (
            "memory",
            "No eligible new reusable decisions; global preferences unchanged; handoff complete.",
        ),
    ):
        path = root / f".auto-bean/artifacts/{stage}/import--{stage}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {stage.title()} outcome\n{text}\n")


def approve(root: Path) -> None:
    import yaml

    path = root / "statements/import-status.yml"
    status = yaml.safe_load(path.read_text())
    for item in status["statements"].values():
        item["current_status"] = "done"
        with (root / item["artifacts"]["import"]).open("a") as stream:
            stream.write(
                "\nExplicit approval: received. User said: I approve the exact validated transaction candidates presented for checking.csv and savings.pdf. Candidate hashes rechecked unchanged and bean-check passed before acceptance.\n"
            )
    path.write_text(yaml.safe_dump(status, sort_keys=False))


def main() -> None:
    from evals.harbor.capture import capture

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("review", "approve"))
    args = parser.parse_args()
    root = Path("/app/ledger")
    plugin = Path("/opt/auto-bean-marketplace/plugins/auto-bean")
    evidence = Path("/opt/eval-evidence")
    if args.phase == "review":
        draft(root, plugin)
    else:
        checkpoint = json.loads((evidence / "review.json").read_text())
        if any(
            sha256(root / relative) != digest
            for relative, digest in checkpoint["financial_hashes"].items()
        ):
            raise RuntimeError("Reviewed candidate changed")
        subprocess.run(
            [
                "sh",
                str(plugin / "runtime/launch.sh"),
                "run",
                "--workspace",
                str(root),
                "bean-check",
                "ledger.beancount",
            ],
            check=True,
        )
        approve(root)
    capture(root, plugin, evidence, "initial" if args.phase == "review" else "approve")
    label = "Ready For Review" if args.phase == "review" else "Complete"
    (evidence / "last-response.txt").write_text(
        "checking.csv and savings.pdf: four transactions, one paired transfer. "
        "Closing balances: 870 EUR checking, 602 EUR savings. Validation passed.\n\n"
        f"---\n\n## Import Status: {label}\n\n**Summary:** Both statements reconciled.\n"
        f"**Next Step:** {'Approve the reviewed changes.' if args.phase == 'review' else 'None.'}\n"
    )


if __name__ == "__main__":
    main()
