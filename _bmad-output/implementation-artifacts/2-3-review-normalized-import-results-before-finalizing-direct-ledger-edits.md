# Story 2.3: Review normalized import results before finalizing direct ledger edits

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a trust-conscious user,
I want to review normalized import results, direct ledger edits, and validation outcomes in one import workflow,
so that I stay in control of what enters my ledger before the agent commits and pushes the result.

## Acceptance Criteria

1. Given a completed import run with normalized statement records and direct ledger edits derived from them, when the system presents the import result, then the user can review the normalized intake result, validation outcome, and resulting diff before commit/push, and the review surface distinguishes parsed transaction records from the ledger changes derived from them, and the workflow makes clear that commit/push remains the final approval boundary.
2. Given an import result contains issues, uncertainty, low-confidence inferences, or failed validation, when the user reviews the result, then the workflow surfaces those concerns clearly before commit/push proceeds, and the user can reject or defer finalization without corrupting existing ledger state.

## Tasks / Subtasks

- [x] Rework the import workflow presentation around a single post-mutation review surface. (AC: 1, 2)
  - [x] Update `skill_sources/auto-bean-import/SKILL.md` so the primary happy path explicitly presents normalized parsed facts, derived ledger edits, validation output, and git-backed diff guidance together before any commit/push request.
  - [x] Keep the import workflow trust model explicit: working-tree mutation may already have happened, but acceptance into history has not happened until the user approves commit/push.
  - [x] Ensure the workflow copy stays deterministic, concise, and stage-based for long-running CLI work.
- [x] Distinguish parsed import facts from derived ledger mutations in workflow contracts and diagnostics. (AC: 1)
  - [x] Preserve `statements/parsed/*.json` and `statements/import-status.yml` as the intake evidence boundary rather than treating them as accepted ledger changes.
  - [x] Require the review summary to call out which normalized records came from statement parsing versus which `ledger.beancount` or `beancount/**` changes were inferred from those records.
  - [x] Keep optional diagnostics under `.auto-bean/artifacts/` or `.auto-bean/proposals/` narrow and inspectable when deeper troubleshooting is needed.
- [x] Block unsafe or unclear finalization paths while preserving inspectability. (AC: 2)
  - [x] Surface validation failures, blocked inferences, low-confidence edits, and ambiguous outcomes before any commit/push prompt.
  - [x] Let the user stop, defer, or reject finalization without corrupting prior accepted ledger history.
  - [x] Record blocked or rejected outcomes as local audit context when the workflow needs durable troubleshooting evidence.
- [x] Align shared mutation guardrails and workspace guidance with the import review boundary. (AC: 1, 2)
  - [x] Update `skill_sources/shared/mutation-pipeline.md` and `skill_sources/shared/mutation-authority-matrix.md` only where needed so they reinforce review-after-mutation, validation-first, and commit/push-gated acceptance.
  - [x] Update workspace-facing guidance if needed so generated workspaces describe review, approval, and recovery consistently with the current import path.
  - [x] Update `README.md` and any affected workspace template guidance so the direct import workflow is described truthfully.

## Dev Notes

- This story is the review counterpart to Story 2.2's direct-mutation rewrite. Story 2.2 moved routine first-seen account creation out of a proposal-first flow and into direct mutation plus validation; Story 2.3 must make that operating model trustworthy and inspectable before commit/push finalization.
- The review surface should stay inside the import workflow rather than bouncing the user into a separate acceptance mode for routine cases. The user should see parsed statement facts, derived ledger edits, validation results, and git-backed inspection guidance together, with a clear statement that commit/push is still the final approval boundary.
- The product repo is not the live ledger workspace. Implementation here should update authored skill behavior, shared policy markdown, tests, and workspace guidance that generated workspaces inherit.
- No separate UX artifact or `project-context.md` was found. UX expectations therefore come from the PRD, architecture, epic wording, and the approved sprint change proposal.

### Technical Requirements

- Keep the primary implementation surface in `skill_sources/auto-bean-import/`.
- Treat `statements/parsed/` and `statements/import-status.yml` as the canonical normalized intake outputs from Story 2.1; Story 2.3 should review and explain those outputs, not redefine their contract.
- Keep direct ledger mutations bounded to the Story 2.2 scope: account-opening structure and minimal supporting directives only. Do not expand this story into transaction posting, transfer handling, duplicate handling, reconciliation, or memory persistence.
- Preserve the standard mutation pipeline: derive structured intent, apply the scoped mutation, validate immediately, summarize the result, present git-backed diff guidance, then ask whether to commit and push.
- When validation fails or the inference is ambiguous, do not present the result as accepted. Preserve enough local audit context for the user to inspect what happened and decide how to proceed.
- Keep all workflow contract keys in `snake_case`.

### Architecture Compliance

- Architecture requires a unified ledger mutation pipeline for all ledger-changing workflows: read inputs, normalize into typed records, build mutation intent, apply mutation, run post-apply validation, produce diff plus summary, ask whether to commit and push, then record audit outcome.
- Architecture and the approved sprint change proposal both place approval at the commit/push boundary rather than a mandatory proposal-before-mutation boundary for routine low-risk import edits.
- Parsed statement records remain inspectable statement-derived data under `statements/parsed/`; they are not the same thing as accepted ledger mutations and the review surface must make that distinction obvious.
- Risky or uncertain outcomes must fail closed. Validation errors, blocked inferences, or low-confidence changes may be shown for inspection, but commit/push must remain blocked until the user explicitly decides what to do next.

### Library / Framework Requirements

- Keep Beancount account-opening edits compatible with `open` directives and optional currency constraints. If Story 2.3 needs to reference why a direct ledger edit matters, it should reflect that an `open` directive defines an account and any allowed currencies, and invalid currency usage is caught during Beancount validation.
- Do not invent a second parser or review subsystem; continue to rely on the existing Docling-driven intake path and the repo's current validation plus git tooling.

### File Structure Requirements

- Likely files to create or modify when implementing this story:
  - `skill_sources/auto-bean-import/SKILL.md`
  - `skill_sources/shared/mutation-pipeline.md`
  - `skill_sources/shared/mutation-authority-matrix.md`
  - `README.md`
  - `workspace_template/AGENTS.md`
  - `src/auto_bean/smoke.py`
  - `tests/test_import_skill_contract.py`
  - `tests/test_setup_diagnostics.py`
  - `tests/test_smoke_checks.py`
- Keep authored skill behavior in `skill_sources/` first; do not add live runtime skills under product-repo `.agents/skills/`.
- Keep product Python changes flat and support-oriented if any helper changes are needed.

### Testing Requirements

- Run `uv run ruff check` and `uv run ruff format` after code changes.
- Run `uv run mypy` when changing Python code.
- Run `uv run pytest` when changing Python code.
- Add or update deterministic tests for:
  - import review summaries that show parsed facts separately from derived ledger edits
  - validation outcome reporting before commit/push approval
  - blocked or uncertain import outcomes that remain inspectable but unfinalized
  - workflow language that makes commit/push the final approval boundary
  - smoke or readiness guidance that reflects the direct import review flow truthfully

### Previous Story Intelligence

- Story 2.1 established the intake boundary and artifacts: raw statements remain under `statements/raw/`, normalized outputs land under `statements/parsed/`, and parse tracking lives in `statements/import-status.yml`. Story 2.3 should build on those artifacts instead of introducing a parallel review contract.
- Story 2.2 already moved the import workflow to direct bounded mutation for routine first-seen account structure. Story 2.3 should not undo that decision by reintroducing proposal-first language for the normal path.
- Story 2.2 emphasized that trust now comes from validation, diff inspection, and commit/push approval after mutation. Story 2.3 is where that trust model becomes concrete and user-visible.
- The current import skill source and shared mutation docs already describe validation plus git-backed diff before finalization. Story 2.3 should bring the review wording, summaries, and tests fully into line with that behavior.

### Git Intelligence

- Recent commits: `8d9a538 story 2.2`, `c6165f0 rewrite story 1.5 and 2.2`, `a448f35 change proposal approval`, `cf45555 story 2.2`, `6f23b50 dev story 2.1`.
- Recent repo activity shows Epic 2 was materially re-scoped on 2026-04-12 around direct mutation plus commit-boundary approval. Story 2.3 should preserve that direction and avoid reintroducing stale proposal-first terminology.

### References

- [Epic breakdown](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/epics.md)
- [PRD](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/prd.md)
- [Architecture](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/architecture.md)
- [Sprint change proposal 2026-04-12](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-12.md)
- [Sprint status](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/sprint-status.yaml)
- [Story 2.1](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/2-1-import-statement-files-into-a-normalized-intake-workflow.md)
- [Story 2.2](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/2-2-create-or-extend-a-ledger-from-first-time-imported-account-statements.md)
- [Import skill source](/Users/sam/Projects/auto-bean/skill_sources/auto-bean-import/SKILL.md)
- [Mutation pipeline](/Users/sam/Projects/auto-bean/skill_sources/shared/mutation-pipeline.md)
- [Mutation authority matrix](/Users/sam/Projects/auto-bean/skill_sources/shared/mutation-authority-matrix.md)
- [Workspace agents guide](/Users/sam/Projects/auto-bean/workspace_template/AGENTS.md)
- [Smoke support](/Users/sam/Projects/auto-bean/src/auto_bean/smoke.py)
- [Import skill contract tests](/Users/sam/Projects/auto-bean/tests/test_import_skill_contract.py)
- [Setup diagnostics tests](/Users/sam/Projects/auto-bean/tests/test_setup_diagnostics.py)
- [Smoke tests](/Users/sam/Projects/auto-bean/tests/test_smoke_checks.py)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story 2.3 created on 2026-04-12 from the current `epics.md`, `prd.md`, `architecture.md`, approved sprint change proposal dated 2026-04-12, `sprint-status.yaml`, Story 2.2, current authored import workflow docs, and recent git history.
- No dedicated UX artifact or `project-context.md` was available, so review-surface guidance was derived from the Epic 2 story wording, FR18, FR35, architecture mutation-pipeline rules, and the direct-mutation sprint change proposal.
- Context7 Beancount docs were consulted to keep the story's direct-edit notes aligned with Beancount `open` directive and validation concepts.
- 2026-04-12 dev implementation started by tightening contract tests first, then updating the authored import workflow, shared mutation policy text, packaged skill prompt, and workspace-facing guidance around a single post-mutation review surface.
- 2026-04-12 validation passed with `uv sync --group dev`, `uv run ruff format`, `uv run ruff check`, `uv run mypy`, and `uv run pytest`.

### Completion Notes List

- Selected the first backlog story in sprint order: `2-3-review-normalized-import-results-before-finalizing-direct-ledger-edits`.
- Created a ready-for-dev story file with implementation tasks, architecture guardrails, previous-story intelligence, and source references.
- Preserved the current Epic 2 operating model: direct bounded mutation for routine import edits, followed by validation, git-backed inspection, and explicit commit/push approval.
- Reworked the authored import workflow so import runs now present a single post-mutation review surface that separates parsed statement facts from derived ledger edits, includes validation outcomes and blocked signals, and keeps commit/push as the final approval boundary.
- Updated shared mutation guardrails, workspace-facing guidance, and the packaged import prompt so generated workspaces describe the same review-after-mutation trust model consistently.
- Extended `tests/test_import_skill_contract.py` to lock in the review-boundary language across the authored skill, shared policy docs, README, workspace guide, and packaged prompt text.

### File List

- _bmad-output/implementation-artifacts/2-3-review-normalized-import-results-before-finalizing-direct-ledger-edits.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- README.md
- skill_sources/auto-bean-import/SKILL.md
- skill_sources/auto-bean-import/agents/openai.yaml
- skill_sources/shared/mutation-authority-matrix.md
- skill_sources/shared/mutation-pipeline.md
- tests/test_import_skill_contract.py
- workspace_template/AGENTS.md
