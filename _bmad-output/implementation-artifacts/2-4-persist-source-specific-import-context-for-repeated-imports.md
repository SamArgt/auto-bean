# Story 2.4: Persist source-specific import context for repeated imports

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a repeat user,
I want source-specific import context to be remembered,
so that repeated imports from the same or similar sources require less setup over time.

## Acceptance Criteria

1. Given a completed import from a recognized source or statement pattern, when the import workflow is finalized, then the system persists source-to-ledger import context needed to improve later runs, and that context is stored in a governed local form consistent with the architecture.
2. Given a later import from the same or similar source, when the import workflow starts, then the system can reuse relevant prior source context to reduce repetitive setup or mapping work, and reused context remains reviewable rather than silently forcing an outcome.

## Tasks / Subtasks

- [x] Define the governed import-context contract and on-disk storage boundary. (AC: 1, 2)
  - [x] Add or update authored references in `skill_sources/auto-bean-import/references/` so repeated-import context has a concrete versioned schema with `snake_case` keys, source identity fields, reuse hints, timestamps, and review metadata.
  - [x] Store persisted source context under a governed workspace path such as `.auto-bean/memory/import_sources/` rather than scattering ad hoc files across `statements/` or `beancount/`.
  - [x] Keep the file format versioned and migration-friendly so future schema changes can be upgraded without introducing a database migration system.
- [x] Teach the authored import workflow when to persist source-specific context. (AC: 1)
  - [x] Update `skill_sources/auto-bean-import/SKILL.md` so import context is written only after a run has reached a trustworthy finalized outcome rather than during blocked, ambiguous, or rejected flows.
  - [x] Persist only bounded source-specific context that helps future imports, such as source identity, statement-shape hints, account-structure reuse hints, or parse/mapping guidance derived from the accepted outcome.
  - [x] Do not expand this story into durable categorization memory, transaction-posting memory, reconciliation decisions, or broader user-preference tuning that belongs to later stories.
- [x] Reuse persisted context at the start of later imports without hiding its influence. (AC: 2)
  - [x] Load matching source context before or during import planning when the same or similar source is recognized from the current statement evidence.
  - [x] Surface what prior context was reused, what current statement evidence still matters, and where the workflow chose not to reuse memory because it no longer fits.
  - [x] Keep reused context reviewable and overrideable; it may guide parsing or account-structure setup, but it must not silently force acceptance or bypass validation and commit/push review.
- [x] Align memory governance, workspace scaffolding, and trust guidance with the new repeated-import behavior. (AC: 1, 2)
  - [x] Update shared workflow guidance so durable memory writes are described as governed operations rather than opportunistic file edits.
  - [x] Extend `workspace_template/AGENTS.md` and related workspace scaffolding so generated workspaces include the expected `.auto-bean/memory/` tree and explain how source-context memory participates in repeated imports.
  - [x] Update `README.md` only where needed so product-facing docs describe repeated-import memory truthfully and keep the local-first trust model explicit.
- [x] Add support-oriented implementation only where markdown guidance is not enough. (AC: 1, 2)
  - [x] Prefer authored skill behavior and workspace template updates first.
  - [x] If deterministic support code is needed, keep it flat and support-oriented in existing modules such as `src/auto_bean/init.py` or `src/auto_bean/smoke.py` rather than introducing layered application architecture.
  - [x] Materialize any new governed memory directories into initialized workspaces through `auto-bean init`, not by hardcoding runtime skills into the product-repo `.agents/skills/`.

## Dev Notes

- Story 2.3 established the post-mutation review boundary for import runs: parsed statement facts, derived ledger edits, validation output, and diff inspection appear together before commit/push approval. Story 2.4 should preserve that trust model and layer reusable source-specific context on top of it rather than bypassing it.
- Epic 2 scope remains bounded to import intake, first-seen account structure, and repeated-import setup reduction. Do not pull transaction posting, transfer detection, duplicate handling, or categorization intelligence forward from Epic 3 or Epic 4.
- The product repo is not the live ledger workspace. Implementation here should update authored skill behavior, memory contracts, workspace scaffolding, smoke checks, and supporting tests that generated workspaces inherit.
- No separate UX artifact or `project-context.md` was found. Reviewability requirements therefore come from the PRD, architecture, Epic 2 story wording, and the direct-mutation change proposal already adopted in Stories 2.2 and 2.3.
- Current authored import guidance explicitly says not to write durable memory under `.auto-bean/memory/**`. This story is the point where that boundary changes in a narrow, governed way for source-specific import context only.

### Technical Requirements

- Keep the primary authored behavior in `skill_sources/auto-bean-import/` and shared markdown guidance.
- Treat `.auto-bean/memory/` as the governed home for durable operational memory, with a narrow subtree for repeated-import source context such as `.auto-bean/memory/import_sources/`.
- Keep all memory keys in `snake_case`, include an explicit schema or format version, and preserve inspectable file-backed records rather than opaque prompt memory.
- Keep persisted context bounded to repeated-import setup and source handling. Do not treat this story as authorization to persist accepted transaction categorizations, reconciliation results, or open-ended user preferences.
- Continue to rely on the existing normalized parse-output contract under `statements/parsed/` and `statements/import-status.yml` as the evidence boundary for import workflows.
- If Python support code is needed for deterministic schema validation or workspace scaffolding, follow the repo's flat-module guidance and keep the CLI surface thin.

### Architecture Compliance

- Architecture requires operational memory to be file-backed, local-first, inspectable, and hidden behind a governed abstraction rather than informal file drops.
- Persist reusable memory only through the governed memory path and keep stable financial state and operational memory clearly separated.
- The import workflow may reuse prior source context to reduce repeated setup work, but reused context must remain reviewable and must not silently force an accepted ledger outcome.
- Validation, diff inspection, and commit/push approval remain the trust boundary for import-derived ledger edits even when memory-assisted reuse is available.

### Library / Framework Requirements

- Use Pydantic v2 models for typed validation at Python-owned workflow boundaries if the implementation introduces support code for memory records. Prefer `model_validate(...)` when loading persisted records and `model_dump(...)` for serialization, with on-disk field names staying `snake_case` by default.
- Prefer explicit compatibility fields or lightweight upgrade transforms over permissive ad hoc parsing when the memory schema evolves.
- Do not introduce a database, ORM, or external persistence dependency for this story; memory remains file-backed in MVP.

### File Structure Requirements

- Likely files to create or modify when implementing this story:
  - `skill_sources/auto-bean-import/SKILL.md`
  - `skill_sources/auto-bean-import/agents/openai.yaml`
  - `skill_sources/auto-bean-import/references/`
  - `skill_sources/shared/mutation-authority-matrix.md`
  - `skill_sources/shared/mutation-pipeline.md`
  - `README.md`
  - `workspace_template/AGENTS.md`
  - `workspace_template/.auto-bean/`
  - `src/auto_bean/init.py`
- Author skill behavior in `skill_sources/` first.
- Do not add live installed runtime skills under product-repo `.agents/skills/`.
- Materialize any new workspace memory directories during `auto-bean init`, not by hardcoding them into unrelated runtime paths.

### Testing Requirements

- Run `uv run ruff check` and `uv run ruff format` after code changes.
- Run `uv run mypy` when changing Python code.
- Run `uv run pytest` when changing Python code.
- Add deterministic tests for:
  - versioned persisted source-context examples and contract keys
  - repeated-import reuse language in the authored import workflow
  - governed `.auto-bean/memory/` workspace scaffolding
  - blocked or rejected import outcomes not writing durable source-context memory
  - reused context being surfaced as reviewable guidance rather than silent acceptance

### Previous Story Intelligence

- Story 2.1 established the normalized intake boundary: raw statements remain under `statements/raw/`, parsed results land under `statements/parsed/`, and parse tracking lives in `statements/import-status.yml`. Story 2.4 should build on that evidence instead of inventing a second intake contract.
- Story 2.2 moved routine first-seen account creation to bounded direct mutation from parsed statement evidence. Source-specific import context should help that workflow repeat cleanly, but it must stay bounded to setup and structure reuse rather than broad ledger automation.
- Story 2.3 made parsed evidence, derived ledger edits, validation, and diff review visible together before commit/push. Story 2.4 should preserve that review boundary when reused context influences a later import.
- Current workspace guidance and import skill text still say durable memory writes are out of scope for import. Implementation will need to update that language deliberately and narrowly rather than leaving contradictory guidance behind.

### Git Intelligence

- Recent commits: `14479d2 story 2.3`, `8d9a538 story 2.2`, `c6165f0 rewrite story 1.5 and 2.2`, `a448f35 change proposal approval`, `cf45555 story 2.2`.
- Recent Epic 2 work concentrated on simplifying import into a direct-mutation plus review model. Story 2.4 should extend that model with governed repeated-import memory, not reopen a proposal-first flow or broaden scope into Epic 3 reconciliation.

### References

- [Epic breakdown](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/epics.md)
- [PRD](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/prd.md)
- [Architecture](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/architecture.md)
- [Sprint change proposal 2026-04-12](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-12.md)
- [Sprint status](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/sprint-status.yaml)
- [Story 2.1](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/2-1-import-statement-files-into-a-normalized-intake-workflow.md)
- [Story 2.2](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/2-2-create-or-extend-a-ledger-from-first-time-imported-account-statements.md)
- [Story 2.3](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/2-3-review-normalized-import-results-before-finalizing-direct-ledger-edits.md)
- [Import skill source](/Users/sam/Projects/auto-bean/skill_sources/auto-bean-import/SKILL.md)
- [Mutation pipeline](/Users/sam/Projects/auto-bean/skill_sources/shared/mutation-pipeline.md)
- [Mutation authority matrix](/Users/sam/Projects/auto-bean/skill_sources/shared/mutation-authority-matrix.md)
- [Workspace agents guide](/Users/sam/Projects/auto-bean/workspace_template/AGENTS.md)
- [Init workflow](/Users/sam/Projects/auto-bean/src/auto_bean/init.py)


## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Add a versioned repeated-import source-context reference contract and narrow the authored import skill boundary around the governed memory path.
- Update the authored import workflow to explain when source context is written, what can be reused, and how reused context stays reviewable.
- Align shared governance docs, workspace scaffolding, init-time asset checks, and product docs so initialized workspaces ship the same memory contract and path structure.
- Add deterministic tests for the contract example, authored skill language, governed workspace scaffolding, and init/package asset coverage before running repo-wide validation.

### Debug Log References

- Story 2.4 created on 2026-04-12 from the current `epics.md`, `prd.md`, `architecture.md`, approved sprint change proposal dated 2026-04-12, `sprint-status.yaml`, Story 2.3, current authored import workflow docs, workspace guidance, and recent git history.
- No dedicated UX artifact or `project-context.md` was available, so reviewability and trust constraints were derived from Epic 2 wording, FR19, architecture memory-governance rules, and the direct-mutation import trust model already established in Stories 2.2 and 2.3.
- Context7 Pydantic v2 docs were consulted to keep the story's memory-record guidance aligned with typed validation and serialization patterns appropriate for versioned file-backed records.
- Marked Story 2.4 `in-progress` in `_bmad-output/implementation-artifacts/sprint-status.yaml` before implementation and advanced it to `review` only after repo-wide validation completed successfully.
- Implemented the story without adding new product modules; support changes stayed in `src/auto_bean/init.py`, `src/auto_bean/smoke.py`, authored skill docs, workspace scaffolding, and deterministic tests.
- Validation completed with `uv run ruff format`, `uv run ruff check`, `uv run mypy`, and `uv run pytest`.

### Completion Notes List

- Selected the first backlog story in sprint order: `2-4-persist-source-specific-import-context-for-repeated-imports`.
- Created a ready-for-dev story file with bounded scope, implementation tasks, memory-governance guardrails, previous-story intelligence, and concrete repository touchpoints.
- Kept Story 2.4 focused on governed repeated-import source context rather than letting it sprawl into categorization memory, reconciliation, or transaction-posting behavior.
- Preserved the current Epic 2 trust model: reused context may guide later imports, but validation, diff inspection, and commit/push approval remain the acceptance boundary for ledger edits.
- Added `skill_sources/auto-bean-import/references/import-source-context.example.json` as the versioned, `snake_case` source-context contract with source identity, reuse hints, timestamps, and review metadata rooted in `.auto-bean/memory/import_sources/`.
- Updated `skill_sources/auto-bean-import/SKILL.md` so repeated-import context is written only after trustworthy finalized outcomes, skipped for blocked or rejected runs, reused during planning as reviewable guidance, and kept out of categorization, posting, reconciliation, or preference memory scope.
- Updated shared trust docs, workspace guidance, README copy, and import skill prompt text so governed runtime memory is described consistently across authored and generated surfaces.
- Materialized `.auto-bean/memory/import_sources/.gitkeep` in the workspace template and aligned `src/auto_bean/init.py` plus `src/auto_bean/smoke.py` with the new required asset set.
- Added deterministic coverage for the new contract, import workflow wording, governed workspace scaffolding, and package/init asset checks; full repo validation passed.

### File List

- README.md
- skill_sources/auto-bean-import/SKILL.md
- skill_sources/auto-bean-import/agents/openai.yaml
- skill_sources/auto-bean-import/references/import-source-context.example.json
- skill_sources/shared/mutation-authority-matrix.md
- skill_sources/shared/mutation-pipeline.md
- src/auto_bean/init.py
- src/auto_bean/smoke.py
- tests/test_import_skill_contract.py
- tests/test_package_foundation.py
- tests/test_setup_diagnostics.py
- workspace_template/AGENTS.md
- workspace_template/.auto-bean/memory/import_sources/.gitkeep
- _bmad-output/implementation-artifacts/2-4-persist-source-specific-import-context-for-repeated-imports.md
- _bmad-output/implementation-artifacts/sprint-status.yaml

### Change Log

- 2026-04-12: Implemented Story 2.4 by adding a governed repeated-import source-context contract, reviewable reuse/persistence guidance, workspace memory scaffolding, init/smoke asset enforcement, and deterministic coverage for the new memory path.
