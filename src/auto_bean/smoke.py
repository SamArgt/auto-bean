from __future__ import annotations

import io
import json
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from auto_bean.cli import main
from auto_bean.init import (
    CommandResult,
    EnvironmentInfo,
    InitService,
    ProjectPaths,
)


@dataclass
class _FakePlatformProbe:
    environment: EnvironmentInfo

    def inspect(self) -> EnvironmentInfo:
        return self.environment


@dataclass
class _FakeToolProbe:
    available_tools: dict[str, str]

    def find(self, command: str) -> str | None:
        return self.available_tools.get(command)


@dataclass
class _FakeCommandRunner:
    responses: dict[tuple[str, ...], CommandResult]

    def run(self, args: object, cwd: Path | None = None) -> CommandResult:
        command = tuple(args) if isinstance(args, (list, tuple)) else tuple()
        if cwd is not None and command[:2] == ("/usr/bin/git", "init"):
            (cwd / ".git").mkdir(parents=True, exist_ok=True)
        if cwd is not None and command[:2] == ("/opt/homebrew/bin/uv", "venv"):
            (cwd / ".venv" / "bin").mkdir(parents=True, exist_ok=True)
            (cwd / ".venv" / "bin" / "python").write_text("", encoding="utf-8")
        if cwd is not None and command[:3] == (
            "/opt/homebrew/bin/uv",
            "pip",
            "install",
        ):
            (cwd / ".venv" / "bin").mkdir(parents=True, exist_ok=True)
            (cwd / ".venv" / "bin" / "bean-check").write_text("", encoding="utf-8")
            (cwd / ".venv" / "bin" / "fava").write_text("", encoding="utf-8")
            (cwd / ".venv" / "bin" / "docling").write_text("", encoding="utf-8")
        return self.responses.get(command, CommandResult(returncode=0))


def _build_service(repo_root: Path) -> InitService:
    return InitService(
        paths=ProjectPaths(start=repo_root),
        platform=_FakePlatformProbe(
            EnvironmentInfo(
                system="Darwin",
                release="24.0.0",
                machine="arm64",
                python_version="3.13.0",
            )
        ),
        tools=_FakeToolProbe({"uv": "/opt/homebrew/bin/uv", "git": "/usr/bin/git"}),
        commands=_FakeCommandRunner({}),
        prompt=lambda _: "Codex",
    )


def run_smoke_checks() -> int:
    with TemporaryDirectory() as tmp_dir:
        repo_root = Path(tmp_dir)
        (repo_root / "src").mkdir()
        (repo_root / "pyproject.toml").write_text(
            "[project]\nname = 'auto-bean'\nversion = '0.1.0'\n",
            encoding="utf-8",
        )
        skill_sources_root = repo_root / "skill_sources"
        (skill_sources_root / "auto-bean-apply" / "scripts").mkdir(parents=True)
        (skill_sources_root / "auto-bean-apply" / "agents").mkdir(parents=True)
        (skill_sources_root / "auto-bean-apply" / "references").mkdir(parents=True)
        (skill_sources_root / "auto-bean-import" / "agents").mkdir(parents=True)
        (skill_sources_root / "auto-bean-import" / "references").mkdir(parents=True)
        (skill_sources_root / "shared").mkdir(parents=True)
        (skill_sources_root / "auto-bean-apply" / "SKILL.md").write_text(
            "\n".join(
                [
                    "# Apply",
                    "Apply scoped structural changes directly in the working tree.",
                    "Turn reviewed parsed statement evidence into candidate Beancount postings when needed.",
                    "Run validation after mutation.",
                    "Keep parsed statement facts separate from derived ledger edits.",
                    "Show git diff before asking whether to commit or push.",
                    "If validation fails or approval is denied, leave the change unfinalized.",
                    "Record audit artifacts under .auto-bean/artifacts/.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (skill_sources_root / "auto-bean-apply" / "agents" / "openai.yaml").write_text(
            'interface:\n  display_name: "Apply"\n  short_description: "Apply changes"\n  default_prompt: "Use $auto-bean-apply."\n',
            encoding="utf-8",
        )
        (
            skill_sources_root
            / "auto-bean-apply"
            / "references"
            / "posting-plan.example.json"
        ).write_text(
            '{"schema_version": "1.0.0", "plan_run_id": "demo", "posting_plan_status": "needs_review", "generated_at": "2026-04-12T19:05:00Z", "source_evidence": [], "ledger_context": {"ledger_entrypoint": "ledger.beancount", "ledger_files_considered": ["ledger.beancount", "beancount/accounts.beancount"], "existing_accounts": ["Assets:Checking"], "declared_currencies": ["EUR"]}, "reused_source_context": [], "candidate_transactions": [], "candidate_mutation": {"target_files": ["ledger.beancount"], "derived_postings_are_unfinalized": true, "validation_required": true}, "review_handoff": {"apply_skill": ".agents/skills/auto-bean-apply/", "mutation_policy_refs": [], "requires_validation_before_apply": true, "requires_explicit_approval": true, "review_surface": ["parsed statement facts", "derived ledger edits", "validation outcome"]}, "blocking_items": []}\n',
            encoding="utf-8",
        )
        (skill_sources_root / "auto-bean-import" / "SKILL.md").write_text(
            "\n".join(
                [
                    "# Import",
                    "Normalize raw statements into statements/parsed/ artifacts.",
                    "Derive bounded first-seen account structure directly from parsed evidence.",
                    "Hand reviewed normalized evidence to auto-bean-apply for transaction postings.",
                    "Validate the ledger after mutation.",
                    "Show git diff before asking whether to commit or push.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (skill_sources_root / "auto-bean-import" / "agents" / "openai.yaml").write_text(
            'interface:\n  display_name: "Import"\n  short_description: "Import statements"\n  default_prompt: "Use $auto-bean-import."\n',
            encoding="utf-8",
        )
        (
            skill_sources_root
            / "auto-bean-import"
            / "references"
            / "account-proposal.example.json"
        ).write_text(
            '{"proposal_run_id": "demo", "proposal_status": "needs_review", "ledger_context": {"baseline_mode": "minimal_generated_baseline", "ledger_entrypoint": "ledger.beancount", "ledger_files_considered": ["ledger.beancount", "beancount/accounts.beancount"], "existing_accounts": ["Assets:Checking"], "existing_operating_currencies": ["EUR"]}, "source_evidence": [], "account_proposals": [{"proposal_kind": "first_seen_candidate", "canonical_account_name": "Assets:Bank:Demo:Checking-1234", "beancount_open_directive": "2026-01-01 open Assets:Bank:Demo:Checking-1234 EUR", "currency_constraints": ["EUR"], "import_derived": true, "evidence_refs": [], "confidence": "high", "issue_notes": [], "review_status": "pending"}], "supporting_directives": {"operating_currency_additions": [], "commodity_declarations": [], "other_structure_notes": []}, "review_handoff": {"apply_skill": ".agents/skills/auto-bean-apply/", "mutation_policy_refs": [], "proposal_artifact_path": ".auto-bean/proposals/demo.json", "would_change_files": ["beancount/accounts.beancount"], "requires_explicit_approval": true, "requires_validation_before_apply": true}, "blocking_inferences": []}\n',
            encoding="utf-8",
        )
        (
            skill_sources_root
            / "auto-bean-import"
            / "references"
            / "import-source-context.example.json"
        ).write_text(
            '{"schema_version": "1.0.0", "context_id": "import-source-context-demo", "source_identity": {"source_slug": "demo", "institution_name": "Demo Bank", "statement_format": "pdf", "account_mask": "1234", "statement_descriptor": "DEMO"}, "reuse_hints": {"statement_shape": {"date_column_labels": ["date"], "amount_column_labels": ["amount"], "balance_column_label": "balance"}, "account_structure": {"primary_account": "Assets:Bank:Demo:Checking-1234", "counterparty_branch": "Expenses:Unknown", "operating_currency": "EUR"}, "parser_guidance": {"preferred_source_format": "pdf", "parse_status_to_reuse": ["parsed"]}}, "review_metadata": {"storage_path": ".auto-bean/memory/import_sources/demo.json", "review_required": true, "derived_from_import_status": true, "reuse_is_advisory_only": true, "last_reviewed_at": "2026-04-12T18:05:00Z"}, "created_at": "2026-04-12T18:00:00Z", "updated_at": "2026-04-12T18:05:00Z"}\n',
            encoding="utf-8",
        )
        (
            skill_sources_root
            / "auto-bean-import"
            / "references"
            / "parsed-statement-output.example.json"
        ).write_text(
            '{"parse_run_id": "demo", "source_file": "statements/raw/demo.pdf", "source_fingerprint": "sha256:demo", "source_format": "pdf", "parser": {"name": "docling"}, "parse_status": "parsed", "parsed_at": "2026-04-11T09:00:00Z", "warnings": [], "blocking_issues": [], "extracted_records": []}\n',
            encoding="utf-8",
        )
        (
            skill_sources_root
            / "auto-bean-import"
            / "references"
            / "import-status.example.yml"
        ).write_text(
            "version: 1\nstatements: {}\n",
            encoding="utf-8",
        )
        (skill_sources_root / "shared" / "mutation-pipeline.md").write_text(
            "# Pipeline\n",
            encoding="utf-8",
        )
        (skill_sources_root / "shared" / "mutation-authority-matrix.md").write_text(
            "# Authority\n",
            encoding="utf-8",
        )
        template_root = repo_root / "workspace_template"
        (template_root / "beancount").mkdir(parents=True)
        (template_root / "docs").mkdir(parents=True)
        (template_root / "statements" / "raw").mkdir(parents=True)
        (template_root / "statements" / "parsed").mkdir(parents=True)
        (template_root / ".auto-bean" / "artifacts").mkdir(parents=True)
        (template_root / ".auto-bean" / "memory" / "import_sources").mkdir(parents=True)
        (template_root / ".auto-bean" / "proposals").mkdir(parents=True)
        (template_root / ".agents").mkdir(parents=True)
        (template_root / "AGENTS.md").write_text(
            "\n".join(
                [
                    "# Agents",
                    "Use direct working-tree edits plus post-mutation validation as the default structural-change flow.",
                    "Show git diff before commit or push approval.",
                    "Require explicit approval before finalization.",
                    "Use git-backed rollback after approved commits.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (template_root / "ledger.beancount").write_text(
            'option "title" "Smoke Ledger"\ninclude "beancount/accounts.beancount"\ninclude "beancount/opening-balances.beancount"\n',
            encoding="utf-8",
        )
        (template_root / "beancount" / "accounts.beancount").write_text(
            "1970-01-01 open Assets:Checking EUR\n1970-01-01 open Equity:Opening-Balances EUR\n",
            encoding="utf-8",
        )
        (template_root / "beancount" / "opening-balances.beancount").write_text(
            "; Opening balance transactions belong here.\n",
            encoding="utf-8",
        )
        (template_root / "docs" / "README.md").write_text("# Docs\n", encoding="utf-8")
        (template_root / "statements" / "parsed" / ".gitkeep").write_text(
            "",
            encoding="utf-8",
        )
        (
            template_root / ".auto-bean" / "memory" / "import_sources" / ".gitkeep"
        ).write_text("", encoding="utf-8")
        (template_root / "statements" / "import-status.yml").write_text(
            "version: 1\nstatements: {}\n",
            encoding="utf-8",
        )
        project_name = f"demo-ledger-{repo_root.name}"

        cases = (
            (
                "init-success",
                ["init", project_name, "--json"],
                _build_service(repo_root),
                0,
            ),
            ("init-blocked", ["init", ".", "--json"], _build_service(repo_root), 1),
        )

        results: list[dict[str, object]] = []
        for name, argv, service, expected_exit in cases:
            buffer = io.StringIO()
            with patch("auto_bean.cli.build_init_service", lambda: service):
                with patch("sys.stdout", buffer):
                    exit_code = main(argv)
            payload = json.loads(buffer.getvalue())
            if name == "init-success":
                workspace_root = repo_root.parent / project_name
                agents_text = workspace_root.joinpath("AGENTS.md").read_text(
                    encoding="utf-8"
                )
                apply_skill_text = workspace_root.joinpath(
                    ".agents", "skills", "auto-bean-apply", "SKILL.md"
                ).read_text(encoding="utf-8")
                import_skill_text = workspace_root.joinpath(
                    ".agents", "skills", "auto-bean-import", "SKILL.md"
                ).read_text(encoding="utf-8")
                required_agents_phrases = (
                    "direct working-tree edits",
                    "git diff before commit or push approval",
                    "explicit approval before finalization",
                    "git-backed rollback",
                )
                required_apply_phrases = (
                    "working tree",
                    "parsed statement facts separate from derived ledger edits",
                    "validation after mutation",
                    "git diff before asking whether to commit or push",
                    "approval is denied",
                    ".auto-bean/artifacts/",
                )
                required_import_phrases = (
                    "statements/parsed/",
                    "first-seen account structure directly",
                    "reviewed normalized evidence to auto-bean-apply",
                    "Validate the ledger after mutation",
                    "git diff before asking whether to commit or push",
                )
                if (
                    not all(phrase in agents_text for phrase in required_agents_phrases)
                    or not all(
                        phrase in apply_skill_text for phrase in required_apply_phrases
                    )
                    or not all(
                        phrase in import_skill_text
                        for phrase in required_import_phrases
                    )
                ):
                    print(
                        json.dumps(
                            {
                                "status": "failed",
                                "reason": "structural_change_guidance_missing",
                                "results": results,
                            },
                            indent=2,
                            sort_keys=True,
                        )
                    )
                    return 1
            results.append(
                {
                    "name": name,
                    "exit_code": exit_code,
                    "expected_exit": expected_exit,
                    "status": payload["status"],
                    "error_code": payload["error_code"],
                }
            )

        if any(item["exit_code"] != item["expected_exit"] for item in results):
            print(
                json.dumps(
                    {"status": "failed", "results": results}, indent=2, sort_keys=True
                )
            )
            return 1

        print(
            json.dumps({"status": "ok", "results": results}, indent=2, sort_keys=True)
        )
        return 0
