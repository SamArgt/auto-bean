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


def test_account_proposal_contract_example_has_required_keys() -> None:
    contract_path = (
        REPO_ROOT
        / "skill_sources"
        / "auto-bean-import"
        / "references"
        / "account-proposal.example.json"
    )

    payload = json.loads(contract_path.read_text(encoding="utf-8"))

    assert set(payload) >= {
        "proposal_run_id",
        "proposal_status",
        "ledger_context",
        "source_evidence",
        "account_proposals",
        "supporting_directives",
        "review_handoff",
        "blocking_inferences",
    }
    assert payload["proposal_status"] == "needs_review"
    assert payload["review_handoff"]["requires_explicit_approval"] is True
    assert payload["review_handoff"]["requires_validation_before_apply"] is True
    assert payload["review_handoff"]["apply_skill"] == ".agents/skills/auto-bean-apply/"
    assert (
        "beancount/accounts.beancount"
        in payload["ledger_context"]["ledger_files_considered"]
    )
    assert payload["review_handoff"]["would_change_files"] == [
        "beancount/accounts.beancount"
    ]
    assert isinstance(payload["source_evidence"], list)
    assert isinstance(payload["account_proposals"], list)
    assert any(
        proposal["proposal_kind"] == "first_seen_candidate"
        for proposal in payload["account_proposals"]
    )


def test_import_skill_documents_docling_status_tracking_review_handoff_and_bounded_parallelism() -> (
    None
):
    skill_path = REPO_ROOT / "skill_sources" / "auto-bean-import" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")

    assert "statements/import-status.yml" in content
    assert "statements/parsed/" in content
    assert ".auto-bean/proposals/" in content
    assert "docling" in content.casefold()
    assert "./.venv/bin/docling" in content
    assert "--to json --output" in content
    assert "parallel workers do not collide" in content
    assert "remove the staged Docling JSON file" in content
    assert "explicitly asks for parallelism or bounded delegation" in content
    assert "first_seen_candidate" in content
    assert 'option "operating_currency" "XYZ"' in content
    assert "Equity:Opening-Balances" in content
    assert "beancount/accounts.beancount" in content
    assert "inspect `beancount/accounts.beancount` first" in content
    assert ".agents/skills/auto-bean-apply/" in content
    assert "do not silently edit `ledger.beancount` or `beancount/**`" in content
    assert "do not mutate `ledger.beancount` or `beancount/**`" in content


def test_import_skill_keeps_ambiguous_or_duplicate_account_cases_review_only() -> None:
    proposal_path = (
        REPO_ROOT
        / "skill_sources"
        / "auto-bean-import"
        / "references"
        / "account-proposal.example.json"
    )
    payload = json.loads(proposal_path.read_text(encoding="utf-8"))

    existing_accounts = payload["ledger_context"]["existing_accounts"]
    proposals = payload["account_proposals"]

    assert "Assets:Checking" in existing_accounts
    assert any(
        proposal["proposal_kind"] == "existing_account"
        and proposal["review_status"] == "no_change"
        for proposal in proposals
    )
    assert payload["blocking_inferences"] == []
