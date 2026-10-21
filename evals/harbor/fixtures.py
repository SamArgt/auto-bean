"""Deterministic synthetic inputs and the independently prepared import ledger."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

SOURCES = ("statements/raw/checking.csv", "statements/raw/savings.pdf")
IDENTITY = {
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_AUTHOR_NAME": "Harbor Fixture",
    "GIT_AUTHOR_EMAIL": "harbor@example.test",
    "GIT_COMMITTER_NAME": "Harbor Fixture",
    "GIT_COMMITTER_EMAIL": "harbor@example.test",
    "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
    "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
}
OPENING = """2025-12-31 * "Opening balances"
  Assets:Checking 1000 EUR
  Assets:Savings 500 EUR
  Equity:Opening-Balances -1500 EUR
"""
ACCOUNTS = """1970-01-01 open Assets:Checking EUR
1970-01-01 open Assets:Savings EUR
1970-01-01 open Expenses:Food EUR
1970-01-01 open Expenses:Bank-Fees EUR
1970-01-01 open Income:Interest EUR
1970-01-01 open Equity:Opening-Balances EUR
"""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=root, env={**os.environ, **IDENTITY}, text=True
    ).strip()


def raw_inputs(directory: Path) -> None:
    """Generate only raw evidence. No parsed answers enter the agent image."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen.canvas import Canvas

    directory.mkdir(parents=True, exist_ok=True)
    (directory / "checking.csv").write_text(
        "Account,Owner,Currency,Period Start,Period End,Opening Balance,Closing Balance,Date,Reference,Description,Amount\n"
        "CHECKING-TEST,Alex Example,EUR,2026-01-01,2026-01-31,1000.00,870.00,2026-01-05,C-001,Example Market,-25.00\n"
        "CHECKING-TEST,Alex Example,EUR,2026-01-01,2026-01-31,1000.00,870.00,2026-01-10,XFER-001,Transfer to own SAVINGS-TEST,-100.00\n"
        "CHECKING-TEST,Alex Example,EUR,2026-01-01,2026-01-31,1000.00,870.00,2026-01-15,C-003,Monthly bank fee,-5.00\n"
    )
    canvas = Canvas(str(directory / "savings.pdf"), pagesize=A4, invariant=1)
    canvas.setTitle("Synthetic January 2026 savings statement")
    lines = [
        "EXAMPLE BANK - SYNTHETIC STATEMENT",
        "Owner: Alex Example",
        "Account: SAVINGS-TEST (Savings) - Currency: EUR",
        "Statement period: 2026-01-01 to 2026-01-31",
        "Opening balance on 2026-01-01: 500.00 EUR",
        "Closing balance on 2026-01-31: 602.00 EUR",
    ]
    canvas.setFont("Helvetica-Bold", 15)
    canvas.drawString(45, 790, lines[0])
    canvas.setFont("Helvetica", 11)
    for index, line in enumerate(lines[1:]):
        canvas.drawString(45, 750 - index * 24, line)
    columns = (45, 130, 220, 495)
    canvas.setFont("Helvetica-Bold", 10)
    for x, label in zip(columns, ("Date", "Reference", "Description", "Amount EUR")):
        canvas.drawString(x, 590, label)
    canvas.line(45, 580, 550, 580)
    canvas.setFont("Helvetica", 10)
    rows = (
        ("2026-01-10", "XFER-001", "From own CHECKING-TEST", "+100.00"),
        ("2026-01-31", "S-002", "Savings interest", "+2.00"),
    )
    for index, row in enumerate(rows):
        for x, value in zip(columns, row):
            canvas.drawString(x, 555 - index * 28, value)
    canvas.setFont("Helvetica", 9)
    canvas.drawString(45, 465, "Synthetic evaluation data. No real account or person.")
    canvas.save()


def import_ledger(root: Path, plugin: Path, raw: Path) -> dict[str, object]:
    """Prepare a committed fixture independently of the init task's outcome."""
    # This helper owns a synthetic fixture destination, never a user ledger.
    # Regeneration replaces its previous contents, including stale artifacts.
    if root.exists():
        shutil.rmtree(root)
    shutil.copytree(plugin / "assets/workspace_template", root, dirs_exist_ok=True)
    write_json(root / ".auto-bean/workspace.json", {"format_version": 1})
    (root / ".gitignore").write_text(
        ".auto-bean/runtime/\n.auto-bean/tmp/\n.auto-bean/migrations/\n"
    )
    (root / "beancount/accounts.beancount").write_text(ACCOUNTS)
    (root / "beancount/opening-balances.beancount").write_text(OPENING)
    (root / "statements/raw").mkdir(parents=True, exist_ok=True)
    (root / "statements/parsed").mkdir(exist_ok=True)
    for name in ("checking.csv", "savings.pdf"):
        shutil.copy2(raw / name, root / "statements/raw" / name)
    (root / "statements/import-status.yml").write_text("version: 1\nstatements: {}\n")
    (root / "personal-notes.txt").write_text("Keep this unrelated user document.\n")
    for args in (
        ("init", "-b", "main"),
        ("add", "--all"),
        ("commit", "-m", "Synthetic starting ledger"),
    ):
        git(root, *args)
    return {
        "head": git(root, "rev-parse", "HEAD"),
        "sources": {path: sha256(root / path) for path in SOURCES},
        "preserved": {
            path: sha256(root / path)
            for path in (
                "personal-notes.txt",
                "beancount/opening-balances.beancount",
                "beancount/accounts.beancount",
                "beancount/prices.beancount",
            )
        },
    }
