# Story 3.2: Detect transfers, duplicates, and unbalanced outcomes during reconciliation

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user reviewing imported ledger changes,
I want likely transfers, duplicates, and unbalanced outcomes flagged,
so that common financial-import errors are caught before acceptance.

## Acceptance Criteria

1. Given candidate transactions from one or more imports, when the reconciliation checks run, then the system identifies likely inter-account transfers, potential duplicate transactions, and unbalanced proposed outcomes, and each issue type is surfaced distinctly for review.
2. Given the workflow detects no safe resolution for a flagged issue, when the review result is presented, then the unresolved issue is preserved as an explicit warning or blocker, and the system does not silently force a misleading ledger result.

## Tasks / Subtasks

- [x] Extend the authored apply workflow to run conservative reconciliation checks before finalization. (AC: 1, 2)
  - [x] Teach `skill_sources/auto-bean-apply/SKILL.md` and its packaged prompt metadata to inspect candidate postings plus current ledger context for likely transfer pairs, possible duplicate matches, and balance-risk conditions.
  - [x] Keep the checks deterministic and evidence-driven: use parsed inputs, existing ledger entries, current candidate postings, and declared account constraints rather than heuristic free-form narration.
  - [x] Fail closed when the workflow cannot safely classify a finding; keep it as a warning or blocker for review instead of guessing a resolution.
- [x] Add focused transfer-detection guidance without turning this story into auto-resolution. (AC: 1, 2)
  - [x] Flag likely inter-account transfers only when counterpart timing, amount, currency, and account context support the inference strongly enough to review.
  - [x] Keep transfer findings reviewable and attributable to the specific candidate postings and parsed statement evidence that triggered them.
  - [x] Do not auto-merge, auto-net, or silently replace candidate postings in this story; clarification and correction workflows belong to later Epic 3 stories.
- [x] Add duplicate-detection guidance that protects against double-booking across repeated imports or overlapping evidence. (AC: 1, 2)
  - [x] Compare candidate postings against existing ledger history and same-run candidate postings using stable reviewable signals such as date windows, payee or narration similarity, amount, currency, account path, links, or imported ids when present.
  - [x] Surface duplicate findings with enough context for the reviewer to understand whether the risk comes from already-booked history, same-run duplication, or overlapping statement evidence.
  - [x] Keep duplicate detection conservative so normal recurring payments are not mislabeled as safe duplicates merely because they look similar.
- [x] Detect and present unbalanced or validation-risk outcomes explicitly. (AC: 1, 2)
  - [x] Check candidate transaction sets for unbalanced postings before any commit/push request and preserve the failing evidence in the review package.
  - [x] Respect Beancount account currency constraints from `open` directives and treat violations or unresolved balancing gaps as blockers rather than auto-fixing with guessed postings.
  - [x] Ensure the review package distinguishes between warnings that may still allow inspection and blockers that must stop finalization.
- [x] Align workspace guidance, packaging, and tests with the new reconciliation-warning boundary. (AC: 1, 2)
  - [x] Update product docs and runtime guidance only where needed so generated workspaces describe how transfer, duplicate, and unbalanced findings appear during `auto-bean-apply`.

## Dev Notes

- Story 3.2 is the first Epic 3 follow-on to Story 3.1's direct-posting workflow. It should not reopen the older proposal-first design or imply that flagged findings must route through a separate acceptance surface.
- The product repo is not the runtime ledger workspace. Implementation here should focus on authored skill behavior, packaged references or examples, workspace guidance, init-time materialization, smoke coverage, and deterministic tests so generated workspaces inherit the same review boundary.
- No separate UX artifact or `project-context.md` was found. Interaction guidance therefore comes from Epic 3 wording, PRD trust requirements, architecture mutation rules, the accepted direct-mutation change proposal, and Story 3.1's commit-gated review boundary.
- Current repo state matters: Story 3.1 references some files that are not present in the working tree today. For this story, prefer the files that actually exist now and only introduce new authored references or support files when they materially improve the review workflow.

### Technical Requirements

- Keep parsed statement evidence under `statements/parsed/` and parse state under `statements/import-status.yml`; reconciliation findings must be derived from reviewed evidence and current ledger context, not from re-parsing raw statements.
- Preserve the two-step workflow boundary: `auto-bean-import` owns normalized inputs and import-state tracking, while `auto-bean-apply` owns reviewed posting mutation, reconciliation checks, validation, diff review, and approval-bound finalization.
- Keep transfer, duplicate, and unbalanced findings explicit and reviewable. Do not silently drop, rewrite, or finalize risky candidate postings merely because a heuristic matched.
- Treat unresolved unbalanced outcomes and currency-constraint violations as blockers. Beancount requires transactions to balance, and `open` directives can constrain which currencies are valid for an account.
- Prefer explicit postings and inspectable evidence even though Beancount can infer one missing balancing amount. This story is about catching risky outcomes, not leaning harder on implicit balancing.
- Reuse governed source-context memory only as advisory guidance. Prior source hints may help account mapping or narration interpretation, but they must not be treated as authority for transfer or duplicate resolution.
- If Python support code is required, keep it flat and support-oriented in existing modules and tests; avoid introducing layered packages or runtime-only abstractions for reconciliation state.

### Architecture Compliance

- Architecture requires a conservative reconciliation and safety-control layer around ledger-changing operations. This story should strengthen that layer by surfacing uncertainty explicitly before commit/push approval.
- Validation, review, diff visibility, approval gating, and auditability remain mandatory cross-cutting concerns. Findings produced here must feed the existing review package rather than creating a competing workflow.
- The architecture remains local-first and file-backed. Do not introduce databases, hosted services, or opaque caches for reconciliation findings in this story.
- Use Pydantic v2-style typed validation patterns when Python support code owns a findings contract, and keep example artifacts or documented contracts versioned and reviewable.
- Worker sub-agents may help analyze large imports in the runtime workflow, but final interpretation of warnings, blocker status, validation outcome, and commit/push approval must remain centralized with the main agent.

### File Structure Requirements

- Likely files to create or modify when implementing this story:
  - `skill_sources/auto-bean-apply/SKILL.md`
  - `skill_sources/auto-bean-apply/agents/openai.yaml`
  - `skill_sources/auto-bean-apply/references/`
  - `skill_sources/shared/beancount-syntax-and-best-practices.md`
  - `skill_sources/auto-bean-import/SKILL.md`
  - `workspace_template/AGENTS.md`
  - `README.md`
  - `src/auto_bean/init.py`
  - `src/auto_bean/smoke.py`
- Author skill behavior in `skill_sources/` first.
- Do not add live runtime skills under product-repo `.agents/skills/`.
- Materialize any new authored references into the user workspace during `auto-bean init`, not by editing installed runtime copies in the product repo.

### Testing Requirements

- Run `uv run ruff check` and `uv run ruff format` after code changes.
- Run `uv run mypy` when changing Python code.
- Run `uv run pytest` when changing Python code.

### Previous Story Intelligence

- Story 3.1 established the candidate-posting boundary: reviewed parsed statement evidence becomes direct working-tree ledger edits only through `auto-bean-apply`, with validation, concise review context, and `git diff` before commit or push.
- Story 2.3 already made the review surface explicit: parsed facts, derived ledger edits, validation outcome, and diff appear together before finalization. Story 3.2 should add issue findings into that surface rather than inventing a second review mode.
- Story 2.4 introduced governed repeated-import source context under `.auto-bean/memory/import_sources/`. Story 3.2 may consult that memory as bounded guidance, but flagged findings must still be anchored in current statement evidence and current ledger state.
- Story 3.1 kept transfer detection, duplicate detection, unresolved balancing diagnostics, and clarification loops deliberately out of scope. Story 3.2 is where those checks start, but only as explicit review findings, not automatic fixes.

### Git Intelligence

- Recent commits: `bf27cd6 story 3.1`, `c197324 nit`, `65a3ee0 nit`, `d5cabf0 wip`, `ba493df wip`.
- Recent repo activity shows a pattern of updating authored skills, README and workspace guidance together, then backing those changes with init-time packaging or smoke/test assertions. Story 3.2 should follow that same product-shape rather than landing isolated prompt edits without packaged coverage.
- The most recent post-3.1 commits were small wording cleanups in `workspace_template/AGENTS.md` and `skill_sources/auto-bean-import/SKILL.md`, which suggests the current workflow language is still being tightened. Any new reconciliation wording should therefore be precise, minimal, and consistent with the existing import/apply split.

### Latest Technical Information

- Current Beancount docs still treat balanced transactions as a hard rule, not a guideline. The workflow should therefore surface unbalanced candidate outcomes as blockers instead of relying on permissive ledger behavior.
- Current Beancount docs also still document `open` directives as the place where account currency constraints are declared. Reconciliation checks should treat those constraints as part of the evidence when deciding whether a candidate outcome is safe.
- Beancount allows one missing balancing amount to be inferred in some cases, but the authored guidance in this repo already prefers explicit, inspectable postings. Story 3.2 should preserve that preference so unbalanced-outcome detection remains reviewable.
- Balance assertions remain a practical guard against duplicate or missing transactions in Beancount-ledger workflows. Even if this story does not author new `balance` directives, its duplicate and unbalanced checks should be designed with that validation model in mind.

### References

- [Epic breakdown](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/epics.md)
- [PRD](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/prd.md)
- [Architecture](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/architecture.md)
- [Sprint change proposal 2026-04-12](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-12.md)
- [Sprint status](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/sprint-status.yaml)
- [Story 2.3](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/2-3-review-normalized-import-results-before-finalizing-direct-ledger-edits.md)
- [Story 2.4](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/2-4-persist-source-specific-import-context-for-repeated-imports.md)
- [Story 3.1](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/3-1-transform-normalized-import-results-into-direct-ledger-postings-with-commit-gated-acceptance.md)
- [Apply skill source](/Users/sam/Projects/auto-bean/skill_sources/auto-bean-apply/SKILL.md)
- [Import skill source](/Users/sam/Projects/auto-bean/skill_sources/auto-bean-import/SKILL.md)
- [Beancount syntax guidance](/Users/sam/Projects/auto-bean/skill_sources/shared/beancount-syntax-and-best-practices.md)
- [Workspace agents guide](/Users/sam/Projects/auto-bean/workspace_template/AGENTS.md)
- [README](/Users/sam/Projects/auto-bean/README.md)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Extend `auto-bean-apply` so it runs conservative reconciliation checks and adds issue findings to the existing validation-plus-diff review boundary before any commit/push request.
- Align runtime guidance so generated workspaces expose the same warning and blocker model consistently.

### Debug Log References

- Story 3.2 created on 2026-04-14 from the current `epics.md`, `prd.md`, `architecture.md`, sprint change proposal dated 2026-04-12, `sprint-status.yaml`, Stories 2.3, 2.4, and 3.1, current authored import/apply workflow docs, workspace guidance, README, and recent git history.
- No dedicated UX artifact or `project-context.md` was available, so interaction requirements were derived from Epic 3 wording, PRD trust requirements, architecture reconciliation and safety-control rules, and the direct-mutation change proposal already adopted in prior stories.
- Context7 Beancount docs were consulted to keep the story's balancing, currency-constraint, and duplicate-risk notes aligned with current Beancount guidance.

### Completion Notes List

- Selected the first backlog story in sprint order: `3-2-detect-transfers-duplicates-and-unbalanced-outcomes-during-reconciliation`.
- Added implementation guardrails that keep transfer, duplicate, and unbalanced checks inside the existing review boundary rather than creating a second approval workflow.
- Scoped the story to conservative detection and reviewable findings only; clarification, corrective action, and broader recovery continue in later Epic 3 stories.
- Added an authored `auto-bean-apply` reconciliation findings reference and updated the packaged prompt metadata so generated workspaces ask for explicit transfer, duplicate, and balance-risk findings with evidence-backed `warning` versus `blocker` status.
- Updated shared Beancount guidance, workspace instructions, and README language so the review package consistently describes conservative reconciliation checks without implying auto-resolution.
- Added packaging and smoke coverage for the new authored reference via `src/auto_bean/init.py`, `src/auto_bean/smoke.py`, and pytest coverage for workspace materialization.
- Validation passed with `uv run ruff check`, `uv run ruff format`, `uv run mypy`, `uv run pytest`, and `uv run python scripts/run_smoke_checks.py`.

### File List

- _bmad-output/implementation-artifacts/3-2-detect-transfers-duplicates-and-unbalanced-outcomes-during-reconciliation.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- README.md
- skill_sources/auto-bean-apply/SKILL.md
- skill_sources/auto-bean-apply/agents/openai.yaml
- skill_sources/auto-bean-apply/references/reconciliation-findings.md
- skill_sources/shared/beancount-syntax-and-best-practices.md
- src/auto_bean/init.py
- src/auto_bean/smoke.py
- tests/test_init.py
- tests/test_smoke.py
- workspace_template/AGENTS.md

### Change Log

- 2026-04-14: Added conservative reconciliation-review guidance for likely transfers, possible duplicates, and unbalanced or currency-risk outcomes, plus packaging and smoke coverage for the new authored reference.
