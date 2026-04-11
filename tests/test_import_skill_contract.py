from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_parsed_statement_contract_example_has_required_keys() -> None:
    contract_path = (
        REPO_ROOT
        / "skill_sources"
        / "auto-bean-import"
        / "references"
        / "parsed-statement-output.example.json"
    )

    payload = json.loads(contract_path.read_text(encoding="utf-8"))

    assert set(payload) >= {
        "parse_run_id",
        "source_file",
        "source_fingerprint",
        "source_format",
        "parser",
        "parse_status",
        "parsed_at",
        "warnings",
        "blocking_issues",
        "extracted_records",
    }
    assert payload["source_file"].startswith("statements/raw/")
    assert isinstance(payload["warnings"], list)
    assert isinstance(payload["blocking_issues"], list)
    assert isinstance(payload["extracted_records"], list)


def test_import_skill_documents_docling_status_tracking_and_bounded_parallelism() -> (
    None
):
    skill_path = REPO_ROOT / "skill_sources" / "auto-bean-import" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")

    assert "statements/import-status.yml" in content
    assert "statements/parsed/" in content
    assert "docling" in content.casefold()
    assert "./.venv/bin/docling" in content
    assert "--to json --output" in content
    assert "parallel workers do not collide" in content
    assert "remove the staged Docling JSON file" in content
    assert "explicitly asks for parallelism or bounded delegation" in content
    assert "do not mutate `ledger.beancount` or `beancount/**`" in content
