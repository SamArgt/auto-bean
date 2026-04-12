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
    assert payload["review_handoff"]["proposal_artifact_path"].startswith(
        ".auto-bean/proposals/"
    )


def test_posting_plan_contract_example_has_required_keys() -> None:
    contract_path = (
        REPO_ROOT
        / "skill_sources"
        / "auto-bean-apply"
        / "references"
        / "posting-plan.example.json"
    )

    payload = json.loads(contract_path.read_text(encoding="utf-8"))

    assert set(payload) >= {
        "schema_version",
        "plan_run_id",
        "posting_plan_status",
        "generated_at",
        "source_evidence",
        "ledger_context",
        "reused_source_context",
        "candidate_transactions",
        "candidate_mutation",
        "review_handoff",
        "blocking_items",
    }
    assert payload["schema_version"].startswith("1.")
    assert payload["posting_plan_status"] == "needs_review"
    assert payload["candidate_mutation"]["derived_postings_are_unfinalized"] is True
    assert payload["candidate_mutation"]["validation_required"] is True
    assert payload["review_handoff"]["requires_explicit_approval"] is True
    assert payload["review_handoff"]["requires_validation_before_apply"] is True
    assert "parsed statement facts" in payload["review_handoff"]["review_surface"]
    assert "derived ledger edits" in payload["review_handoff"]["review_surface"]
    assert "validation outcome" in payload["review_handoff"]["review_surface"]
    assert isinstance(payload["candidate_transactions"], list)
    assert isinstance(payload["reused_source_context"], list)
    assert isinstance(payload["blocking_items"], list)


def test_import_source_context_contract_example_is_versioned_and_governed() -> None:
    contract_path = (
        REPO_ROOT
        / "skill_sources"
        / "auto-bean-import"
        / "references"
        / "import-source-context.example.json"
    )

    payload = json.loads(contract_path.read_text(encoding="utf-8"))

    assert set(payload) >= {
        "schema_version",
        "context_id",
        "source_identity",
        "reuse_hints",
        "review_metadata",
        "created_at",
        "updated_at",
    }
    assert payload["schema_version"].startswith("1.")
    assert payload["context_id"].startswith("import-source-context-")
    assert payload["review_metadata"]["storage_path"].startswith(
        ".auto-bean/memory/import_sources/"
    )
    assert payload["review_metadata"]["review_required"] is True
    assert payload["review_metadata"]["derived_from_import_status"] is True


def test_import_skill_documents_docling_status_tracking_direct_mutation_and_bounded_parallelism() -> (
    None
):
    skill_path = REPO_ROOT / "skill_sources" / "auto-bean-import" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")

    assert "statements/import-status.yml" in content
    assert "statements/parsed/" in content
    assert ".auto-bean/proposals/" in content
    assert ".auto-bean/artifacts/" in content
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
    assert "create bounded first-seen ledger account structure directly" in content
    assert "run the standard ledger validation gate after direct mutation" in content
    assert "single post-mutation review surface" in content
    assert "parsed statement facts" in content
    assert "derived ledger edits" in content
    assert "commit/push remains the final approval boundary" in content
    assert "stop, defer, or reject finalization" in content
    assert "show a git-backed diff" in content
    assert "ask whether the agent should commit and push" in content
    assert "do not create transaction postings" in content
    assert "keep the mutation deterministic" in content


def test_import_skill_references_governed_source_context_memory_contract() -> None:
    skill_path = REPO_ROOT / "skill_sources" / "auto-bean-import" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")

    assert "import-source-context.example.json" in content
    assert ".auto-bean/memory/import_sources/" in content
    assert "snake_case" in content
    assert "schema_version" in content
    assert "migration-friendly" in content


def test_import_skill_limits_persisted_source_context_to_trustworthy_finalized_runs() -> (
    None
):
    skill_path = REPO_ROOT / "skill_sources" / "auto-bean-import" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")

    assert (
        "suggest source-context create or update actions only after a trustworthy finalized outcome"
        in content
    )
    assert (
        "let the orchestrator decide whether to actually write the source-context file"
        in content
    )
    assert (
        "do not suggest source-context writes for blocked, ambiguous, rejected"
        in content
    )
    assert "source identity" in content
    assert "statement-shape hints" in content
    assert "account-structure reuse hints" in content
    assert "parse or mapping guidance" in content
    assert "do not persist categorization memory" in content
    assert "do not persist transaction-posting memory" in content
    assert "do not persist reconciliation decisions" in content
    assert "do not persist open-ended user-preference tuning" in content


def test_import_skill_reuses_persisted_source_context_as_reviewable_guidance() -> None:
    skill_path = REPO_ROOT / "skill_sources" / "auto-bean-import" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")

    assert "load matching source context before or during import planning" in content
    assert (
        "return a concrete suggestion for the orchestrator instead of writing it directly"
        in content
    )
    assert "surface what prior context was reused" in content
    assert "what current statement evidence still matters" in content
    assert "where the workflow chose not to reuse memory" in content
    assert "reused context reviewable and overrideable" in content
    assert "must not silently force acceptance" in content
    assert "must not silently bypass validation and commit/push review" in content


def test_import_skill_optional_diagnostic_proposal_keeps_duplicate_accounts_as_no_change() -> (
    None
):
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


def test_apply_skill_documents_direct_mutation_diff_approval_and_audit_flow() -> None:
    skill_path = REPO_ROOT / "skill_sources" / "auto-bean-apply" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")

    assert "working tree" in content
    assert "posting-plan.example.json" in content
    assert "reviewed `statements/parsed/*.json` inputs" in content
    assert "keep parsed statement facts separate from derived ledger edits" in content
    assert ".auto-bean/memory/import_sources/" in content
    assert "Context7" in content
    assert "post-mutation validation" in content
    assert "git diff" in content
    assert "commit or push" in content
    assert ".auto-bean/proposals/" in content
    assert "optional review aids" in content
    assert "unfinalized" in content
    assert "validation fails" in content
    assert "low confidence" in content


def test_shared_mutation_policy_prefers_direct_mutation_with_commit_gated_finalization() -> (
    None
):
    pipeline = (
        REPO_ROOT / "skill_sources" / "shared" / "mutation-pipeline.md"
    ).read_text(encoding="utf-8")
    matrix = (
        REPO_ROOT / "skill_sources" / "shared" / "mutation-authority-matrix.md"
    ).read_text(encoding="utf-8")

    assert "Apply the scoped mutation in the local working tree" in pipeline
    assert "Keep the mutation bounded to the workflow's scope" in pipeline
    assert "summary plus `git diff`" in pipeline
    assert "approval is denied" in pipeline
    assert "review package" in pipeline
    assert "parsed evidence" in pipeline
    assert "derived ledger mutation" in pipeline
    assert "structured posting plan" in pipeline
    assert "accepted into history" in pipeline
    assert "auto-bean-import" in matrix
    assert "Direct working-tree mutation" in matrix
    assert "parsed statement outputs remain intake evidence" in matrix
    assert "Reviewed import posting plans" in matrix
    assert "advisory only" in matrix
    assert "Blocked or rejected outcomes" in matrix
    assert "Diff inspection" in matrix
    assert "Commit/push finalization" in matrix
    assert "high-scrutiny operation" in matrix


def test_workspace_and_readme_describe_import_review_boundary_truthfully() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    workspace_agents = (REPO_ROOT / "workspace_template" / "AGENTS.md").read_text(
        encoding="utf-8"
    )
    prompt_text = (
        REPO_ROOT / "skill_sources" / "auto-bean-import" / "agents" / "openai.yaml"
    ).read_text(encoding="utf-8")

    assert "single review surface" in readme
    assert "parsed statement facts" in readme
    assert "derived ledger edits" in readme
    assert "commit/push approval before the change is accepted into history" in readme
    assert "stop, defer, or reject finalization" in readme
    assert ".auto-bean/memory/import_sources/" in readme
    assert "repeated-import source context" in readme
    assert "governed runtime memory" in readme

    assert "Import Workflow" in workspace_agents
    assert "1. `auto-bean-import`" in workspace_agents
    assert "2. `auto-bean-apply`" in workspace_agents
    assert "Worker Handoff" in workspace_agents
    assert "one worker handles the `auto-bean-import` stage" in workspace_agents
    assert "one worker handles the `auto-bean-apply` stage" in workspace_agents
    assert "validation outcome" in workspace_agents
    assert "stop, defer, or reject finalization" in workspace_agents
    assert "accepted into git history" in workspace_agents
    assert ".auto-bean/memory/import_sources/" in workspace_agents
    assert "Skills may suggest useful repeated-import memory." in workspace_agents
    assert (
        "The orchestrator decides whether that memory should actually be written."
        in workspace_agents
    )
    assert "`auto-bean-import` prepares evidence." in workspace_agents
    assert "`auto-bean-apply` performs reviewed posting mutation." in workspace_agents

    assert "parsed statement facts" in prompt_text
    assert "$auto-bean-apply" in prompt_text


def test_shared_mutation_docs_describe_governed_memory_writes() -> None:
    pipeline = (
        REPO_ROOT / "skill_sources" / "shared" / "mutation-pipeline.md"
    ).read_text(encoding="utf-8")
    matrix = (
        REPO_ROOT / "skill_sources" / "shared" / "mutation-authority-matrix.md"
    ).read_text(encoding="utf-8")

    assert "governed operation" in pipeline
    assert ".auto-bean/memory/import_sources/" in pipeline
    assert "reviewable" in pipeline
    assert "source-specific import context" in matrix
    assert ".auto-bean/memory/import_sources/" in matrix


def test_init_requires_and_smoke_materializes_posting_plan_assets() -> None:
    init_text = (REPO_ROOT / "src" / "auto_bean" / "init.py").read_text(
        encoding="utf-8"
    )
    smoke_text = (REPO_ROOT / "src" / "auto_bean" / "smoke.py").read_text(
        encoding="utf-8"
    )

    assert "auto-bean-apply/references/posting-plan.example.json" in init_text
    assert "posting-plan.example.json" in smoke_text
    assert "reviewed normalized evidence to auto-bean-apply" in smoke_text
