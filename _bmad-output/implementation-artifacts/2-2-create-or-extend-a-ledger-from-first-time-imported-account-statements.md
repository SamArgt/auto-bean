# Story 2.2: Create or extend a ledger from first-time imported account statements

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a first-time or expanding ledger user,
I want first-seen accounts to be proposed through statement import,
so that account creation happens principally from real imported account evidence rather than separate manual setup.

## Acceptance Criteria

1. Given a normalized parsed statement result for an account not yet represented in `ledger.beancount` or `beancount/**`, when the import workflow analyzes the parsed account evidence, then the system produces a first-seen account proposal as part of the import result, and the proposal clearly marks the account as import-derived and not yet accepted into the canonical ledger.
2. Given the user starts from the default generated ledger or another incomplete ledger, when imported account data provides enough evidence to proceed, then the system can prepare the structural additions needed to extend that ledger or establish a richer baseline from imported account data, and standalone manual account creation is not required for the normal first-seen path.
3. Given imported account evidence is missing, ambiguous, or conflicts with existing ledger structure, when the workflow prepares the proposal, then the system surfaces the uncertainty, preserves the current ledger unchanged, and routes the result into the explicit review-and-approval workflow instead of silently mutating `ledger.beancount` or `beancount/**`.

## Tasks / Subtasks

- [x] Define the first-seen account proposal contract on top of Story 2.1 parsed outputs. (AC: 1, 2, 3)
  - [x] Add or document a structured proposal artifact that links each proposed account to its parsed-statement evidence, source file, source fingerprint, parse run id, and confidence or issue notes.
  - [x] Keep the proposal contract narrow: account-structure planning only, not transaction postings, transfer detection, duplicate handling, durable memory writes, or final ledger mutation.
  - [x] Distinguish clearly between an already-existing ledger account, a first-seen candidate account, and a blocked or ambiguous account inference.
- [x] Extend the authored import workflow in `skill_sources/auto-bean-import/` to derive first-seen account structure from normalized parsed statements. (AC: 1, 2, 3)
  - [x] Teach the import skill to inspect `statements/parsed/` outputs and identify account-level evidence such as institution name, account type hints, statement currency, masked account numbers, and statement labels.
  - [x] Prefer extending the existing authored import skill over inventing a separate import-orchestration surface.
  - [x] Keep authored behavior in `skill_sources/` first, and use Python only for bounded helpers if markdown guidance alone cannot keep the workflow deterministic.
- [x] Propose Beancount-safe account structure without directly applying it. (AC: 1, 2, 3)
  - [x] Generate candidate Beancount `open` directives for first-seen accounts using canonical account names and optional currency constraints when the evidence supports them.
  - [x] Propose any needed supporting structure such as `Equity:Opening-Balances`, commodity declarations, or `operating_currency` additions only when the imported account evidence justifies them and the current ledger does not already contain the requirement.
  - [x] Keep proposals reviewable and separate from accepted ledger files until the explicit apply path succeeds.
- [x] Support both extending an existing ledger and enriching the generated baseline ledger. (AC: 2, 3)
  - [x] When the workspace still has the minimal generated baseline ledger, allow the workflow to propose replacing or extending that baseline with import-derived accounts instead of requiring the user to hand-author accounts first.
  - [x] When the workspace already has related account structure, propose only the missing additions and avoid duplicating existing accounts, commodities, or operating-currency declarations.
  - [x] Fail closed when the parsed evidence is insufficient to determine whether the account belongs under `Assets`, `Liabilities`, `Income`, `Expenses`, or another branch.
- [x] Reuse the existing structural review boundary instead of inventing a second approval system. (AC: 1, 3)
  - [x] Route structurally meaningful proposals through the installed `auto-bean-apply` workflow and the shared mutation-policy files rather than bypassing them.
  - [x] Make the import result explain what structure is being proposed, why it was inferred from the statement, which files would change, and what still needs user validation.
  - [x] Preserve governed proposal and diagnostic artifacts under `.auto-bean/` when deeper review or troubleshooting is needed.
- [x] Preserve ledger, import, and memory boundaries. (AC: 1, 2, 3)
  - [x] Do not create transaction postings, reconciliation candidates, duplicate decisions, transfer decisions, or mutation plans for accepted ledger edits in this story.
  - [x] Do not write durable memory under `.auto-bean/memory/**`; source-specific reuse belongs to Story 2.4.
  - [x] Keep `statements/parsed/` as the source evidence boundary and keep canonical ledger files unchanged unless and until the explicit reviewed apply path is approved in-workspace.
- [x] Add deterministic verification and documentation for the new proposal workflow. (AC: 1, 2, 3)
  - [x] Add tests for first-seen account detection from normalized parsed outputs, including extend-ledger, enrich-baseline, duplicate-account, and ambiguous-evidence cases.
  - [x] Add a skill-contract test that the authored import workflow explicitly routes structural proposals through review rather than silently editing ledger files.
  - [x] Update maintainer and workspace-facing docs only enough to describe the new first-seen account proposal capability truthfully, while keeping it clear that transaction reconciliation and final review happen in later stories.

## Dev Notes

- Story 2.1 already established the import intake boundary: raw statements become normalized parse artifacts under `statements/parsed/`, with parse-state tracking in `statements/import-status.yml`, and no ledger mutation. Story 2.2 should build directly on those parsed outputs instead of re-parsing files or introducing a second intake format.
- Epic 2 makes first-seen account creation part of the import path. This story should therefore plan account structure from imported evidence, not send the user back to a separate manual account-setup workflow.
- The repo's trust model is already in place from Story 1.5: materially meaningful structural ledger changes must go through explicit summary, validation, and approval. Story 2.2 should reuse that review boundary rather than inventing a shortcut for import-derived account creation.
- The product repo is not the live ledger workspace. Any accepted ledger edits, proposal artifacts, and review steps happen in generated user workspaces; the product repo should only author the workflow and its supporting helpers.
- No UX artifact or `project-context.md` exists. Trust-sensitive behavior therefore needs to stay explicit in the story, skill text, result contracts, and tests.

### Technical Requirements

- Keep the primary implementation surface in `skill_sources/auto-bean-import/` and reuse `skill_sources/auto-bean-apply/` plus `skill_sources/shared/mutation-pipeline.md` and `skill_sources/shared/mutation-authority-matrix.md` for reviewed structural changes.
- Follow the product repo's flat Python layout. Prefer extending `src/auto_bean/init.py`, `src/auto_bean/cli.py`, `src/auto_bean/smoke.py`, or focused tests over reintroducing layered `application/`, `domain/`, or `infrastructure/` packages unless a genuinely independent concern emerges.
- Keep any structured helper outputs in `snake_case` and treat them as internal workflow contracts, not a public API.
- Reuse Story 2.1 parsed-statement contract fields such as `parse_run_id`, `source_file`, `source_fingerprint`, `source_format`, `warnings`, `blocking_issues`, and extracted records rather than inventing a separate evidence envelope.
- Keep proposal generation deterministic for the same parsed input unless the user intentionally changes the ledger, the authored workflow, or proposal rules.

### Architecture Compliance

- The architecture says statement parsing should flow through the local Docling CLI into normalized outputs, after which auto-bean owns orchestration and ledger safety boundaries. Story 2.2 starts after parsing and should operate on normalized outputs rather than adding bespoke parser code.
- The architecture also requires explicit approval before risky structural changes. First-seen account creation is structurally meaningful, so proposals must remain inspectable and unaccepted until the reviewed apply path succeeds.
- Keep the local-first boundary intact: primary evidence, proposals, diagnostics, and accepted ledger changes stay in workspace files, with no cloud dependency required for this story.
- Preserve the separation between stable user-owned assets and evolving tool logic: runtime ledger files live in the workspace, while product-authored behavior lives in `skill_sources/` and supporting package files in this repo.

### Library / Tool Requirements

- Continue to treat the workspace-local Docling CLI as the statement-parsing path established in Story 2.1; Story 2.2 should consume normalized outputs from that flow, not replace it. Source: [Docling README](https://github.com/docling-project/docling/blob/main/README.md)
- Use Beancount account-opening syntax when proposing new accounts. Official examples show `open` directives with optional currency constraints such as `2014-05-01 open Liabilities:CreditCard:CapitalOne USD` and `2001-05-29 open Assets:Checking USD,EUR`. Source: [Beancount language syntax](https://beancount.github.io/docs/index.html/beancount_language_syntax), [Beancount cheat sheet](https://beancount.github.io/docs/index.html/beancount_cheat_sheet)
- When imported evidence introduces a new operating currency, prefer proposing an `option "operating_currency" "XYZ"` addition instead of silently relying on an undeclared reporting currency. Source: [Running Beancount and Generating Reports](https://beancount.github.io/docs/index.html/running_beancount_and_generating_reports)
- Commodity directives are optional in Beancount and should be proposed only when metadata or early declaration is actually useful for the imported account path. Source: [Beancount Commodity directive](https://beancount.github.io/docs/api_reference/beancount.core.html)
- Keep using `./.venv/bin/bean-check ledger.beancount` or `./scripts/validate-ledger.sh` as the validation gate before any reviewed structural change is presented as ready. Source: [Workspace agents guide](/Users/sam/Projects/auto-bean/workspace_template/AGENTS.md)

### File Structure Requirements

- Likely files to create or modify when implementing this story:
  - `skill_sources/auto-bean-import/SKILL.md`
  - `skill_sources/auto-bean-import/references/` for any proposal-contract example or decision reference
  - `skill_sources/auto-bean-apply/SKILL.md` only if the review handoff for import-derived structure needs clarification
  - `skill_sources/shared/mutation-pipeline.md`
  - `skill_sources/shared/mutation-authority-matrix.md`
  - `workspace_template/AGENTS.md`
  - `README.md` if the supported scope description changes
  - `src/auto_bean/init.py` only if workspace scaffolding or install-time guidance must expose the new proposal capability
  - `src/auto_bean/smoke.py` and focused tests if smoke coverage needs a representative first-seen account proposal scenario
  - `tests/test_import_skill_contract.py`
  - `tests/test_setup_diagnostics.py` only if template/runtime expectations change
- Do not add bespoke Python parser modules for statement ingestion.
- Do not add live runtime skills under product-repo `.agents/skills/`.
- Do not write accepted ledger changes directly in the product repo; accepted mutations belong in the generated workspace.

### Testing Requirements

- Run `uv run ruff check` and `uv run ruff format` after code changes.
- Run `uv run mypy` when changing Python code.
- Run `uv run pytest` when changing Python code.
- Add deterministic tests for:
  - detecting a first-seen account from normalized parsed inputs
  - skipping proposals when the account already exists in the ledger
  - enriching the minimal baseline ledger without duplicating `Assets:Checking` or `Equity:Opening-Balances`
  - surfacing ambiguous evidence without mutating ledger files
  - routing structurally meaningful changes through explicit review and validation
- Keep existing Story 2.1 import-contract coverage and smoke checks passing.

### Previous Story Intelligence

- Story 2.1 already chose the core surfaces for Epic 2: `skill_sources/auto-bean-import/`, `statements/parsed/`, `statements/import-status.yml`, and workspace-local Docling. Story 2.2 should extend those surfaces rather than redirecting the flow into new runtime locations.
- Story 2.1 explicitly deferred account proposals, reconciliation, mutation, and memory. Story 2.2 is the first place account-structure planning should appear, but it must still stop short of reconciliation and durable memory.
- Story 1.5 already created the skill-first review/apply boundary for structural changes. Reuse it for import-derived account additions.
- The current repo now uses a flat package layout under `src/auto_bean/` and focused tests such as `tests/test_import_skill_contract.py`; avoid following older artifact notes that still mention layered package paths.

### Git Intelligence

- Recent history shows this sequence: `3b042df create story 2-1`, `ed76263 correct course`, `6f23b50 dev story 2.1`. Story 2.2 should assume Story 2.1 implementation exists and build on its actual authored import skill rather than re-scoping import intake again.
- Prior story work bundled story artifacts and sprint tracking updates together. Keep the story file and `sprint-status.yaml` synchronized for this new context artifact as well.

### Latest Technical Information

- Current Beancount docs still describe explicit `open` directives for new accounts and allow optional currency constraints on those directives, which is directly relevant for import-derived account proposals. Sources: [Beancount language syntax](https://beancount.github.io/docs/index.html/beancount_language_syntax), [Beancount cheat sheet](https://beancount.github.io/docs/index.html/beancount_cheat_sheet)
- Current Beancount docs still document repeated `option "operating_currency" "..."` declarations when a ledger needs multiple reporting currencies. Source: [Running Beancount and Generating Reports](https://beancount.github.io/docs/index.html/running_beancount_and_generating_reports)
- Current official and repo guidance still favor Docling for document conversion and the existing workspace-local import flow for normalized statement outputs. Sources: [Docling README](https://github.com/docling-project/docling/blob/main/README.md), [Story 2.1](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/2-1-import-statement-files-into-a-normalized-intake-workflow.md)

### References

- [Epic breakdown](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/epics.md)
- [Architecture](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/architecture.md)
- [PRD](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/prd.md)
- [Sprint status](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/sprint-status.yaml)
- [Story 2.1](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/2-1-import-statement-files-into-a-normalized-intake-workflow.md)
- [Story 1.5](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/1-5-review-and-approve-structural-ledger-changes-through-the-agent-workflow.md)
- [Import skill source](/Users/sam/Projects/auto-bean/skill_sources/auto-bean-import/SKILL.md)
- [Apply skill source](/Users/sam/Projects/auto-bean/skill_sources/auto-bean-apply/SKILL.md)
- [Workspace agents guide](/Users/sam/Projects/auto-bean/workspace_template/AGENTS.md)
- [Workspace ledger template](/Users/sam/Projects/auto-bean/workspace_template/ledger.beancount)
- [Workspace opening balances](/Users/sam/Projects/auto-bean/workspace_template/beancount/opening-balances.beancount)
- [Init workflow](/Users/sam/Projects/auto-bean/src/auto_bean/init.py)
- [Import skill contract tests](/Users/sam/Projects/auto-bean/tests/test_import_skill_contract.py)
- [README](/Users/sam/Projects/auto-bean/README.md)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story 2.2 created on 2026-04-11 from the first backlog story in `sprint-status.yaml`.
- Context synthesized from Epic 2, the PRD, the architecture document, Story 2.1, Story 1.5, the current authored import/apply skills, workspace guidance, current repo structure, recent git history, and current Beancount/Docling references.
- The story was optimized to prevent a common regression: reintroducing direct ledger mutation or a second approval system instead of reusing the existing skill-first review boundary.
- The story also corrects for stale artifact drift by pointing the developer at the current flat `src/auto_bean/` layout instead of older layered-path notes.
- Implemented the first-seen account proposal contract in the authored import skill and added an example proposal artifact under `skill_sources/auto-bean-import/references/account-proposal.example.json`.
- Updated workspace and maintainer guidance so the import workflow truthfully describes reviewable first-seen account proposals without implying silent ledger mutation.
- Verified the Story 2.2 changes with `uv run ruff check`, `uv run ruff format`, `uv run mypy`, and `uv run pytest`.
- Follow-up on 2026-04-11: added `beancount/accounts.beancount` to the workspace template, moved baseline account openings there, and taught the import skill to inspect that file first for account discovery.

### Completion Notes List

- Selected the next backlog item automatically from `sprint-status.yaml`: `2-2-create-or-extend-a-ledger-from-first-time-imported-account-statements`.
- Produced a developer-focused story that reuses Story 2.1 parsed outputs and Story 1.5 approval boundaries.
- Added Beancount-specific guardrails for `open` directives, optional currency constraints, `operating_currency`, and optional commodity declarations.
- Kept scope bounded to account-structure proposals and review handoff, not reconciliation, transaction posting, or durable memory.
- Extended `skill_sources/auto-bean-import/SKILL.md` so the import workflow now derives first-seen account proposals from normalized parsed statements, classifies existing versus new versus blocked inferences, and routes structural review through `auto-bean-apply`.
- Added a deterministic example proposal contract and test coverage for review handoff, duplicate-account handling, and first-seen proposal presence.
- Updated `README.md` and `workspace_template/AGENTS.md` so Story 2.2 is documented as proposal-oriented and still approval-gated.
- Split workspace account structure from opening balance content by introducing `beancount/accounts.beancount` and pointing template, init validation, smoke scaffolding, and tests at that convention.

### File List

- _bmad-output/implementation-artifacts/2-2-create-or-extend-a-ledger-from-first-time-imported-account-statements.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- README.md
- skill_sources/auto-bean-import/SKILL.md
- skill_sources/auto-bean-import/agents/openai.yaml
- skill_sources/auto-bean-import/references/account-proposal.example.json
- src/auto_bean/init.py
- src/auto_bean/smoke.py
- tests/test_import_skill_contract.py
- tests/test_package_foundation.py
- tests/test_setup_diagnostics.py
- workspace_template/AGENTS.md
- workspace_template/beancount/accounts.beancount
- workspace_template/beancount/opening-balances.beancount
- workspace_template/ledger.beancount

## Change Log

- 2026-04-11: Implemented Story 2.2 first-seen account proposal workflow, added the proposal contract example, updated docs, and expanded import skill contract coverage.
- 2026-04-11: Added a dedicated workspace `beancount/accounts.beancount` file and taught import account discovery to prefer it.
