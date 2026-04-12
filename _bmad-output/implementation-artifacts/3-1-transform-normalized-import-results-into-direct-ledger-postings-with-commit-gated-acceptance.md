# Story 3.1: Transform normalized import results into direct ledger postings with commit-gated acceptance

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user importing real financial activity,
I want normalized imported transactions transformed into direct ledger postings,
so that reviewed statement data can be turned into validated accounting changes that I can inspect before commit/push.

## Acceptance Criteria

1. Given normalized imported transactions that have passed the Epic 2 import review and an existing ledger context, when the reconciliation workflow runs, then the system transforms the imported transactions into ledger postings mapped to appropriate ledger accounts, and the resulting change is summarized and shown through a git-backed diff before commit/push.
2. Given imported transactions include patterns seen before, when the mapping workflow evaluates them, then relevant prior mappings may be reused to improve the resulting postings, and reused mappings remain attributable and reviewable.

## Tasks / Subtasks

- [x] Define the transaction-posting reconciliation contract and workflow boundary. (AC: 1, 2)
  - [x] Add or update authored reference material for a versioned, inspectable posting-plan artifact that links normalized `statements/parsed/` evidence, ledger-context inputs, inferred postings, reviewable reuse of prior source context, and commit-gated acceptance metadata.
  - [x] Keep parsed statement outputs as intake evidence and keep derived postings separate from accepted ledger history until validation succeeds and the user approves finalization.
  - [x] Preserve the two-step workflow boundary: `skill_sources/auto-bean-import/` owns normalized inputs, first-seen account structure, and governed source memory, while transaction-posting mutation routes through `skill_sources/auto-bean-apply/` and shared mutation guidance rather than ad hoc import logic.
  - [x] Review `workspace_template/AGENTS.md` from top to bottom and rewrite it as needed so the end-to-end import process is explicit without duplication: `auto-bean-import` for normalized inputs, first-seen account structure, and import-source memory, then `auto-bean-apply` for direct ledger mutation, validation, diff review, and approval-bound finalization.
- [x] Extend the authored workflow to transform normalized import results into candidate Beancount transactions. (AC: 1)
  - [x] Teach the relevant authored skill flow to load reviewed `statements/parsed/*.json`, current ledger context, and any bounded prior source context from `.auto-bean/memory/import_sources/` before building postings.
  - [x] Generate balanced Beancount transaction entries with explicit account mappings, stable date and narration handling, and enough source references that the user can see how parsed statement facts became ledger edits.
  - [x] Keep this story focused on straightforward transaction posting from already-reviewed normalized imports; do not fold transfer detection, duplicate detection, unresolved balancing diagnostics, or clarification loops into the same implementation.
- [x] Preserve reviewability and trust when prior mappings influence posting generation. (AC: 2)
  - [x] Surface which prior source-context hints were reused, which current statement facts still drove the outcome, and where prior hints were ignored because they no longer fit the present import.
  - [x] Keep reused guidance advisory and attributable; prior context may improve mapping but must not silently force an accepted posting result.
  - [x] Record any durable audit or troubleshooting artifacts under governed runtime paths without conflating them with accepted ledger history.
- [x] Present direct posting mutations through the existing validation-and-diff review boundary. (AC: 1, 2)
  - [x] Reuse the shared mutation pipeline so candidate postings are applied in the working tree, validated, summarized, diffed, and only then offered for commit/push approval.
  - [x] Keep the review surface explicit about the difference between parsed statement evidence, derived posting edits in `ledger.beancount` or `beancount/**`, and accepted git history.
  - [x] Ensure blocked or low-confidence posting outcomes fail closed for later stories instead of being represented as safe successful imports.
- [x] Add support-oriented product changes and deterministic coverage where markdown guidance alone is not enough. (AC: 1, 2)
  - [x] Update workspace guidance, packaged prompts, smoke scaffolding, and init-time materialization only where needed so generated workspaces ship the same posting-workflow boundary consistently.
  - [x] Update workflow guidance so the agent explicitly consults Beancount documentation through Context7 when it needs authoritative rules for transaction syntax, postings, account directives, or validation constraints.
  - [x] Update `workspace_template/AGENTS.md` so the runtime import workflow explicitly allows bounded worker sub-agents during import or reconciliation work when they help keep statement analysis, evidence review, or posting derivation within context limits without blurring final approval boundaries.
  - [x] Keep Python support changes flat and support-oriented in existing modules such as `src/auto_bean/init.py` or `src/auto_bean/smoke.py` if packaging or validation helpers are required.

## Dev Notes

- Story 3.1 is the first Epic 3 step after Epic 2 established three critical boundaries: normalized statement facts live under `statements/parsed/`, direct account-structure edits may already happen from parsed evidence, and commit/push approval remains the final trust boundary after post-mutation validation and diff review.
- This story should add transaction posting, not reopen the proposal-first architecture that was intentionally collapsed. The user should still see direct working-tree edits, validation, concise review context, and `git diff` before commit or push.
- The product repo is not the runtime ledger workspace. Implementation here should change authored skill behavior, shared mutation policy, packaging/materialization support, workspace guidance, and tests that generated workspaces inherit.
- No separate UX artifact or `project-context.md` was found. Interaction requirements therefore come from the Epic 3 wording, PRD trust constraints, architecture mutation rules, the approved direct-mutation change proposal, and the Epic 2 stories already created.
- `workspace_template/AGENTS.md` should be treated as a concise runtime operating guide rather than an append-only changelog. Story implementation should review the entire document, consolidate overlapping trust-model language, and make the full import-to-apply workflow explicit in one coherent pass.
- `workspace_template/AGENTS.md` should also describe when the runtime workflow may use worker sub-agents during the import process itself, for example to split bounded statement-analysis or posting-derivation work while keeping approval and final review with the main agent.

### Technical Requirements

- Preserve `statements/parsed/` and `statements/import-status.yml` as the import evidence boundary; do not re-parse raw statements or blur parsed evidence together with accepted ledger history.
- Keep transaction-posting mutation on the reviewed ledger-mutation path. `skill_sources/auto-bean-import/` may still gather or explain parsed evidence, but canonical posting edits should follow the `auto-bean-apply` and shared mutation-policy boundary for validation, diff review, and commit/push gating.
- Preserve the workflow split clearly: `auto-bean-import` handles normalized inputs, first-seen account structure, and governed import-source memory, while `auto-bean-apply` handles direct ledger mutation from reviewed evidence.
- Reuse bounded prior source context from `.auto-bean/memory/import_sources/` only as reviewable guidance for mapping or narration defaults; do not treat prior context as authority to skip current-evidence checks or acceptance review.
- Generate valid Beancount transaction entries that stay balanced and traceable back to normalized statement facts. Respect existing account names and any currency constraints already declared in `open` directives.
- Keep this story scoped to straightforward posting generation from already-reviewed normalized imports. Transfer detection, duplicate detection, unbalanced-outcome handling, clarification loops, rollback flows, and broader learned categorization belong to later Epic 3, 4, or 5 stories.
- Use Context7 Beancount documentation as the primary reference whenever the implementation needs authoritative guidance on transaction syntax, balancing behavior, account directives, or validation rules.
- Review `workspace_template/AGENTS.md` holistically during implementation and prefer consolidation over accretion; the final guidance should describe the full import workflow clearly without repeating the same boundary in multiple sections.
- When `workspace_template/AGENTS.md` is revised for this story, make worker-subagent usage part of the runtime workflow guidance itself: bounded parallel help for large imports is allowed, but final review, validation interpretation, and commit/push approval must remain centralized and explicit.
- If support code is introduced for typed posting-plan validation, keep it flat, package-support oriented, and consistent with the repo's existing `src/auto_bean/` boundaries.

### Architecture Compliance

- Architecture requires the standard ledger mutation pipeline: inspect inputs, derive structured intent, apply the mutation in the working tree, run post-apply validation, produce a concise summary and diff, ask whether to commit/push, and record audit outcome.
- Canonical `ledger.beancount` and `beancount/**` changes remain high-scrutiny trust-boundary operations. This story must not imply that generated postings are accepted merely because they were written locally.
- Parsed statement artifacts remain statement-derived evidence, while derived posting edits are candidate mutations. The workflow and any reference artifacts must keep those states distinct.
- Reused source-specific import context must remain file-backed, local-first, reviewable, and bounded. The workflow may benefit from prior context, but acceptance still depends on present evidence, validation, and explicit approval.

### Library / Framework Requirements

- Beancount transaction generation should follow normal double-entry transaction structure: dated transaction entries with payee or narration context and balanced postings that can be validated by Beancount tooling. Favor explicit, inspectable postings over opaque shortcuts.
- Existing Beancount `open` directives may restrict allowed currencies for an account. Any generated posting flow must either respect those constraints or surface a validation failure rather than writing misleading accepted output.
- Consult Beancount documentation through Context7 before encoding posting-shape assumptions, balancing behavior, or directive syntax in authored workflow guidance or support code.
- If Python-owned schema validation is added for posting-plan artifacts or structured results, use Pydantic v2 patterns already expected in this repo, with `snake_case` fields and explicit schema-version handling.
- Do not introduce a database, ORM, or remote dependency for reconciliation state in this story; the product remains local-first and file-backed.

### File Structure Requirements

- Likely files to create or modify when implementing this story:
  - `skill_sources/auto-bean-apply/SKILL.md`
  - `skill_sources/auto-bean-apply/agents/openai.yaml`
  - `skill_sources/auto-bean-apply/references/`
  - `skill_sources/auto-bean-import/SKILL.md`
  - `skill_sources/shared/mutation-pipeline.md`
  - `skill_sources/shared/mutation-authority-matrix.md`
  - `workspace_template/AGENTS.md`
  - `README.md`
  - `src/auto_bean/init.py`
- Author skill behavior in `skill_sources/` first.
- Do not add live runtime skills under product-repo `.agents/skills/`.
- Materialize any new authored skill references or runtime guidance through `auto-bean init`, not by hand-editing installed runtime copies in the product repo.

### Testing Requirements

- Run `uv run ruff check` and `uv run ruff format` after code changes.
- Run `uv run mypy` when changing Python code.
- Run `uv run pytest` when changing Python code.
- Add deterministic tests for:
  - the posting-plan example contract and required `snake_case` keys
  - separation between parsed statement evidence and derived posting edits
  - reviewable reuse of `.auto-bean/memory/import_sources/` hints during posting generation
  - commit/push-gated acceptance wording in authored skills, workspace guidance, and packaged prompts
  - validation-failure or low-confidence outcomes remaining unfinalized
  - consolidated `workspace_template/AGENTS.md` guidance reflecting the explicit two-step import workflow without duplicate or contradictory instructions

### Previous Story Intelligence

- Story 2.1 established the normalized intake boundary: raw statements stay in `statements/raw/`, normalized outputs land in `statements/parsed/`, and parse tracking lives in `statements/import-status.yml`. Story 3.1 should build on that evidence instead of inventing a second import substrate.
- Story 2.2 already moved bounded first-seen account structure into direct mutation from parsed evidence. Story 3.1 should preserve that direct-mutation trust model while extending it to transaction postings.
- Story 2.3 made the review surface concrete: parsed statement facts, derived ledger edits, validation outcome, and git-backed diff appear together before commit/push approval. Story 3.1 should reuse that surface for transaction postings rather than creating a new acceptance mode.
- Story 2.4 introduced governed repeated-import source context under `.auto-bean/memory/import_sources/`. Story 3.1 is the first story that may reuse that context to improve posting generation, but the reuse must stay advisory and reviewable.

### Git Intelligence

- Recent commits: `311cb61 story 2.4`, `14479d2 story 2.3`, `8d9a538 story 2.2`, `c6165f0 rewrite story 1.5 and 2.2`, `a448f35 change proposal approval`.
- Recent repo activity shows a deliberate shift toward direct mutation plus commit-boundary approval. Story 3.1 should continue that direction and avoid reintroducing mandatory proposal-first acceptance for routine import-derived postings.

### Latest Technical Information

- Context7 Beancount docs confirm the core transaction shape for imported ledger entries: a dated transaction with payee or narration text and balanced postings, where Beancount can interpolate a missing balancing amount when appropriate. Story 3.1 should still prefer reviewable, explicit derived postings when generating import-driven ledger edits.
- Context7 Beancount docs also confirm that `open` directives can constrain account currencies and that those constraints are checked during validation. Generated posting flows should therefore respect existing account constraints or fail closed during validation rather than treating invalid currency usage as accepted output.

### References

- [Epic breakdown](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/epics.md)
- [PRD](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/prd.md)
- [Architecture](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/architecture.md)
- [Sprint change proposal 2026-04-12](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-12.md)
- [Sprint status](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/sprint-status.yaml)
- [Story 2.1](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/2-1-import-statement-files-into-a-normalized-intake-workflow.md)
- [Story 2.2](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/2-2-create-or-extend-a-ledger-from-first-time-imported-account-statements.md)
- [Story 2.3](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/2-3-review-normalized-import-results-before-finalizing-direct-ledger-edits.md)
- [Story 2.4](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/2-4-persist-source-specific-import-context-for-repeated-imports.md)
- [Import skill source](/Users/sam/Projects/auto-bean/skill_sources/auto-bean-import/SKILL.md)
- [Apply skill source](/Users/sam/Projects/auto-bean/skill_sources/auto-bean-apply/SKILL.md)
- [Mutation pipeline](/Users/sam/Projects/auto-bean/skill_sources/shared/mutation-pipeline.md)
- [Mutation authority matrix](/Users/sam/Projects/auto-bean/skill_sources/shared/mutation-authority-matrix.md)
- [Workspace agents guide](/Users/sam/Projects/auto-bean/workspace_template/AGENTS.md)
- [README](/Users/sam/Projects/auto-bean/README.md)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Define a versioned posting-plan contract that keeps parsed evidence, derived posting edits, advisory memory reuse, and commit-gated acceptance metadata separate and inspectable.
- Extend the reviewed mutation workflow so transaction postings are generated from normalized imports and validated through the same summary-plus-diff boundary already used for direct mutation work.
- Align authored skills, shared policy docs, packaged prompts, workspace guidance around the new posting-generation boundary.

### Debug Log References

- Story 3.1 created on 2026-04-12 from the current `epics.md`, `prd.md`, `architecture.md`, approved sprint change proposal dated 2026-04-12, `sprint-status.yaml`, Stories 2.1 through 2.4, current authored import/apply workflow docs, workspace guidance, and recent git history.
- No dedicated UX artifact or `project-context.md` was available, so trust and interaction guidance was derived from the Epic 3 wording, FR35-FR37 style safety requirements, architecture mutation-pipeline rules, and the direct-mutation change proposal already adopted in Epic 2.
- Context7 Beancount docs were consulted to keep the story's transaction-posting and account-currency notes aligned with current Beancount guidance for balanced transactions and `open` directive constraints.
- Added `skill_sources/auto-bean-apply/references/posting-plan.example.json` as the versioned contract for reviewed parsed evidence, advisory source-context reuse, candidate transactions, and commit-gated review metadata.
- Updated `skill_sources/auto-bean-apply/`, `skill_sources/auto-bean-import/`, and shared mutation docs so transaction postings route through `auto-bean-apply`, while `auto-bean-import` remains the authority for normalized inputs, first-seen account structure, and governed import-source memory.
- Updated workspace/runtime guidance, init-time asset checks, smoke scaffolding, and deterministic tests to keep the two-step import-to-apply workflow materialized consistently.
- Verification completed successfully with `uv run ruff check`, `uv run ruff format`, `uv run mypy`, and `uv run pytest`.

### Completion Notes List

- Selected the first backlog story in sprint order: `3-1-transform-normalized-import-results-into-direct-ledger-postings-with-commit-gated-acceptance`.
- Added a versioned posting-plan example contract and corresponding `auto-bean-apply` workflow guidance for reviewed import-derived transaction postings.
- Preserved the two-step workflow boundary: `auto-bean-import` owns normalized inputs and governed import memory, while `auto-bean-apply` owns reviewed transaction-posting mutation, validation, diff review, and approval-bound finalization.
- Rewrote `workspace_template/AGENTS.md` in one coherent pass so the runtime workflow now states the explicit import-to-apply flow, advisory memory reuse, and bounded worker-subagent rules without duplicating earlier trust-model language.
- Extended init-time asset checks, smoke scaffolding, and deterministic tests so generated workspaces consistently include the posting-plan reference and the new workflow wording.
- Verified the implementation with `uv run ruff check`, `uv run ruff format`, `uv run mypy`, and `uv run pytest` with all tests passing.

### File List

- _bmad-output/implementation-artifacts/3-1-transform-normalized-import-results-into-direct-ledger-postings-with-commit-gated-acceptance.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- README.md
- skill_sources/auto-bean-apply/SKILL.md
- skill_sources/auto-bean-apply/agents/openai.yaml
- skill_sources/auto-bean-apply/references/posting-plan.example.json
- skill_sources/auto-bean-import/SKILL.md
- skill_sources/auto-bean-import/agents/openai.yaml
- skill_sources/shared/mutation-authority-matrix.md
- skill_sources/shared/mutation-pipeline.md
- src/auto_bean/init.py
- src/auto_bean/smoke.py
- tests/test_import_skill_contract.py
- tests/test_package_foundation.py
- tests/test_setup_diagnostics.py
- workspace_template/AGENTS.md

### Change Log

- 2026-04-12: Added the posting-plan contract, split import versus apply transaction authority explicitly, refreshed workspace guidance and prompt metadata, and extended init/smoke/test coverage for Story 3.1.
