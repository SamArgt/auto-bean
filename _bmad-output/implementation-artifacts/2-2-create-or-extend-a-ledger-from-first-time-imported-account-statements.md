# Story 2.2: Create or extend a ledger from first-time imported account statements

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a first-time or expanding ledger user,
I want the agent to create or extend the ledger directly from first-time imported account statements when the evidence is sufficient,
so that account creation happens principally from real imported account evidence rather than separate manual setup.

## Acceptance Criteria

1. Given a normalized parsed statement result for an account not yet represented in `ledger.beancount` or `beancount/**`, when the import workflow analyzes the parsed account evidence and the inference is sufficiently confident, then the system writes the new account structure needed for that imported account directly into the ledger as part of the import workflow, and the workflow makes clear that the account was first-seen and import-derived.
2. Given the user starts from the default generated ledger or another incomplete ledger, when imported account data provides enough evidence to proceed, then the system can create a richer ledger baseline or extend the existing ledger from that imported account data, standalone manual account creation is not required for the normal first-seen path, validation runs immediately after mutation, and the workflow shows the resulting diff before asking whether the agent should commit and push the change.
3. Given imported account evidence is missing, ambiguous, structurally risky, or causes validation to fail, when the workflow derives the ledger update, then the system pauses instead of guessing or finalizing, preserves the current change as unfinalized workspace state, and surfaces what was inferred, what remains uncertain, and what the user should inspect before any commit or push.

## Tasks / Subtasks

- [x] Rewrite the authored import workflow around direct mutation for first-seen accounts. (AC: 1, 2, 3)
  - [x] Update `skill_sources/auto-bean-import/SKILL.md` so Story 2.2 no longer stops at proposal-only account structure for the normal first-seen path.
  - [x] Keep the primary implementation surface in `skill_sources/` and use Python helpers only when markdown guidance cannot keep the workflow deterministic.
  - [x] Remove or rewrite instructions that currently require `.auto-bean/proposals/` or `auto-bean-apply` as the mandatory path for routine import-derived account creation.
- [x] Derive direct account-structure edits from Story 2.1 parsed outputs and current ledger state. (AC: 1, 2, 3)
  - [x] Reuse `statements/parsed/` outputs and `statements/import-status.yml` rather than re-parsing source statements or inventing a second evidence contract.
  - [x] Inspect `beancount/accounts.beancount`, `ledger.beancount`, and included `beancount/**` files to distinguish existing accounts from first-seen candidates.
  - [x] Infer Beancount-safe account names, optional currency constraints, and any minimal supporting directives only when the parsed evidence justifies them.
- [x] Write direct ledger mutations safely and keep them bounded to account structure. (AC: 1, 2, 3)
  - [x] Prefer adding or extending account-opening structure in `beancount/accounts.beancount` when that file is present, while preserving the current workspace layout.
  - [x] Allow creation or extension of a usable baseline ledger from imported account evidence without requiring separate manual account setup first.
  - [x] Do not create transaction postings, reconciliation outcomes, duplicate handling, transfer handling, or durable memory writes in this story.
- [x] Validate immediately after mutation and present inspectable change context. (AC: 2, 3)
  - [x] Run the standard ledger validation gate after direct mutation and never present a failed validation result as success.
  - [x] Summarize which files changed, what account structure was inferred, and why that inference was made from the imported statement evidence.
  - [x] Show a git-backed diff and ask whether the agent should commit and push only after the direct mutation and validation result are available.
- [x] Fail closed for ambiguity, risky structure, or invalid results. (AC: 3)
  - [x] Block finalization when the evidence does not support a stable top-level Beancount branch or otherwise leaves the structural inference unclear.
  - [x] Block finalization when validation fails, while preserving enough local audit context for inspection and troubleshooting.
  - [x] Use `.auto-bean/proposals/` or `.auto-bean/artifacts/` only as optional diagnostics when deeper review or troubleshooting is warranted, not as the default workflow boundary.
- [x] Update tests, smoke coverage, and docs for the direct-mutation import path. (AC: 1, 2, 3)
  - [x] Replace proposal-first contract assertions in `tests/test_import_skill_contract.py` with direct-mutation, validation, and commit-gated inspection assertions.
  - [x] Update `tests/test_setup_diagnostics.py`, `tests/test_smoke_checks.py`, and any focused smoke scaffolding if workspace guidance or safety expectations change.
  - [x] Update `README.md` and `workspace_template/AGENTS.md` so they describe direct import-derived ledger mutation truthfully, including validation, diff inspection, and commit/push approval.

## Dev Notes

- This rewrite follows the approved sprint change proposal dated 2026-04-12, which removes proposal-first account creation as the normal Epic 2 path and makes direct mutation plus validation and git-backed inspection the primary workflow.
- Story 2.1 remains the intake boundary: raw statements become normalized parse artifacts under `statements/parsed/`, with parse tracking in `statements/import-status.yml`. Story 2.2 should build on those parsed outputs instead of re-parsing files or changing the intake contract.
- Epic 2 now owns the direct import-to-ledger path for routine high-confidence structure creation. This story should create or extend account structure directly when confidence is sufficient, then surface validation and diff context before commit/push.
- Trust still matters, but the approval point has moved. The user should inspect the resulting diff and validation outcome after mutation and before commit/push finalization, rather than reviewing a required proposal artifact before mutation.
- The product repo is not the live ledger workspace. Implementation here should author the workflow, tests, and workspace guidance that generated workspaces will use.
- No separate UX artifact or `project-context.md` was found. Trust-sensitive behavior therefore needs to stay explicit in this story, the authored skill text, the shared mutation guidance, and tests.

### Technical Requirements

- Keep the primary implementation surface in `skill_sources/auto-bean-import/`.
- Rework `skill_sources/shared/mutation-pipeline.md` and `skill_sources/shared/mutation-authority-matrix.md` as needed so they match direct mutation with validation and commit-gated finalization.
- Treat `skill_sources/auto-bean-apply/` as optional follow-up scope only if it still has a useful role for exceptional review, troubleshooting, or recovery after this workflow change; do not keep it as a mandatory boundary for routine first-seen account creation.
- Follow the product repo's flat Python layout. Prefer extending `src/auto_bean/init.py`, `src/auto_bean/smoke.py`, or focused tests over introducing layered packages.
- Keep any helper outputs in `snake_case` and treat them as internal workflow contracts, not a public API.
- Keep direct mutations deterministic for the same parsed inputs and ledger state unless the user intentionally changes the workspace, the workflow, or relevant config.

### Architecture Compliance

- The current planning artifacts now describe risky edits and structural changes as direct mutations surfaced through validation and git-backed inspection before commit/push finalization. Story 2.2 should follow that model.
- Story 2.2 may mutate `beancount/**` for routine first-seen account structure when it follows the standard mutation pipeline: derive structured intent, mutate, validate, summarize, show diff, and ask for commit/push approval.
- Proposal artifacts are now optional diagnostics rather than the normal import boundary. Do not preserve proposal-only semantics as the main success path.
- Keep the local-first boundary intact: statement evidence, resulting ledger files, validation outputs, diffs, and optional troubleshooting artifacts stay in the workspace with no cloud dependency required for this story.

### File Structure Requirements

- Likely files to create or modify when implementing this story:
  - `skill_sources/auto-bean-import/SKILL.md`
  - `skill_sources/shared/mutation-pipeline.md`
  - `skill_sources/shared/mutation-authority-matrix.md`
  - `skill_sources/auto-bean-apply/SKILL.md` only if it is being repurposed for exceptional review or recovery rather than routine import structure changes
  - `README.md`
  - `workspace_template/AGENTS.md`
  - `src/auto_bean/init.py`
  - `src/auto_bean/smoke.py`
  - `tests/test_import_skill_contract.py`
  - `tests/test_setup_diagnostics.py`
  - `tests/test_smoke_checks.py`
- Prefer existing workspace ledger structure files such as `beancount/accounts.beancount`, `beancount/opening-balances.beancount`, and `ledger.beancount` over inventing a new baseline layout.
- Do not add live runtime skills under product-repo `.agents/skills/`.
- Do not add proposal-only runtime storage as a required part of the standard import path.

### Testing Requirements

- Run `uv run ruff check` and `uv run ruff format` after code changes.
- Run `uv run mypy` when changing Python code.
- Run `uv run pytest` when changing Python code.
- Add deterministic tests for:
  - direct creation of a first-seen account from normalized parsed inputs
  - extending an existing ledger without duplicating accounts or supporting directives
  - enriching the generated baseline ledger from imported account evidence
  - blocking finalization when account inference is ambiguous or structurally risky
  - blocking finalization when validation fails after mutation
  - surfacing validation results and git-backed diff guidance before commit/push
- Remove or update tests that still require proposal-only success for routine first-seen account creation.

### Previous Story Intelligence

- Story 2.1 already established the import surfaces for Epic 2: `skill_sources/auto-bean-import/`, `statements/parsed/`, `statements/import-status.yml`, and workspace-local Docling. Story 2.2 should extend those surfaces rather than redirecting the flow into a separate proposal workflow.
- Story 2.1 intentionally stopped before account creation, reconciliation, mutation, and memory. Story 2.2 is the first story that should cross the mutation boundary for account structure, but it should stay bounded to direct structural edits plus validation and inspection.
- Story 1.5 is semantically affected by the change proposal: its trust and finalization guidance should now be interpreted as commit/push-gated inspection and recovery rather than mandatory proposal-first review for all structural changes.
- Recent repo history shows Story 2.2 was previously authored and partially implemented around proposal-first semantics. Rewriting this story should prevent further work from cementing the deprecated model.

### Git Intelligence

- Recent commits: `a448f35 change proposal approval`, `cf45555 story 2.2`, `6f23b50 dev story 2.1`, `ed76263 correct course`, `3b042df create story 2-1`.
- Story and sprint tracking had drifted: this story file still said `review` while `sprint-status.yaml` marked 2.2 as `backlog`. This rewrite resets Story 2.2 to a clean `ready-for-dev` planning state aligned with the approved direction.

### References

- [Sprint change proposal 2026-04-12](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-12.md)
- [Epic breakdown](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/epics.md)
- [PRD](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/prd.md)
- [Architecture](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/architecture.md)
- [Sprint status](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/sprint-status.yaml)
- [Story 2.1](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/2-1-import-statement-files-into-a-normalized-intake-workflow.md)
- [Story 1.5](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/1-5-inspect-and-finalize-structural-ledger-changes-through-the-agent-workflow.md)
- [Import skill source](/Users/sam/Projects/auto-bean/skill_sources/auto-bean-import/SKILL.md)
- [Apply skill source](/Users/sam/Projects/auto-bean/skill_sources/auto-bean-apply/SKILL.md)
- [Mutation pipeline](/Users/sam/Projects/auto-bean/skill_sources/shared/mutation-pipeline.md)
- [Mutation authority matrix](/Users/sam/Projects/auto-bean/skill_sources/shared/mutation-authority-matrix.md)
- [Workspace agents guide](/Users/sam/Projects/auto-bean/workspace_template/AGENTS.md)
- [Workspace ledger template](/Users/sam/Projects/auto-bean/workspace_template/ledger.beancount)
- [Workspace accounts file](/Users/sam/Projects/auto-bean/workspace_template/beancount/accounts.beancount)
- [Workspace opening balances](/Users/sam/Projects/auto-bean/workspace_template/beancount/opening-balances.beancount)
- [Init workflow](/Users/sam/Projects/auto-bean/src/auto_bean/init.py)
- [Smoke support](/Users/sam/Projects/auto-bean/src/auto_bean/smoke.py)
- [Import skill contract tests](/Users/sam/Projects/auto-bean/tests/test_import_skill_contract.py)
- [Setup diagnostics tests](/Users/sam/Projects/auto-bean/tests/test_setup_diagnostics.py)
- [Smoke tests](/Users/sam/Projects/auto-bean/tests/test_smoke_checks.py)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story 2.2 rewritten on 2026-04-12 to align with the approved sprint change proposal that shifts Epic 2 from proposal-first account creation to direct mutation plus validation and git-backed inspection.
- Context synthesized from the latest sprint change proposal, current `epics.md`, `prd.md`, `architecture.md`, `sprint-status.yaml`, Story 2.1, Story 1.5, current authored skill sources, and recent git history.
- Replaced stale proposal-only guidance with bounded direct-mutation guidance while preserving safety through validation, diff inspection, and commit/push approval.
- Updated smoke and setup diagnostics fixtures so the packaged workspace checks now cover import-driven direct mutation guidance as well as the apply workflow boundary.
- Verified the implementation with `uv run ruff check /Users/sam/Projects/auto-bean`, `uv run ruff format /Users/sam/Projects/auto-bean`, `uv run mypy /Users/sam/Projects/auto-bean/src /Users/sam/Projects/auto-bean/tests`, and `uv run pytest /Users/sam/Projects/auto-bean/tests`.

### Completion Notes List

- Rewrote Story 2.2 around direct import-derived ledger mutation for routine first-seen account creation.
- Kept scope bounded to account structure, validation, inspection, and commit/push approval.
- Explicitly blocked ambiguous, risky, or invalid outcomes from being finalized.
- Marked proposal artifacts as optional diagnostics instead of the default workflow boundary.
- Updated the import skill UI metadata, shared mutation policy, workspace guidance, and README so the direct-mutation trust model is described consistently.
- Extended smoke/setup test coverage so generated workspaces are checked for the new import guidance instead of only the apply guidance.

### File List

- _bmad-output/implementation-artifacts/2-2-create-or-extend-a-ledger-from-first-time-imported-account-statements.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- README.md
- skill_sources/auto-bean-import/SKILL.md
- skill_sources/auto-bean-import/agents/openai.yaml
- skill_sources/shared/mutation-authority-matrix.md
- skill_sources/shared/mutation-pipeline.md
- src/auto_bean/smoke.py
- tests/test_import_skill_contract.py
- tests/test_setup_diagnostics.py
- tests/test_smoke_checks.py
- workspace_template/AGENTS.md

## Change Log

- 2026-04-12: Rewrote Story 2.2 to match the approved direct-mutation sprint change proposal and reset the story to ready-for-dev.
- 2026-04-12: Implemented the direct-mutation import workflow rewrite, updated shared/workspace docs, and refreshed smoke plus contract coverage for commit-gated inspection.
