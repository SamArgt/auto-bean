# Story 4.3: Inspect stored memory that influences future behavior

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user maintaining trust in the system,
I want to inspect learned memory entries,
so that I can understand what prior decisions may affect future results.

## Acceptance Criteria

1. Given governed memory has been accumulated over prior workflows, when the user runs the memory inspection workflow, then the system presents stored memory entries in a reviewable form and entries are understandable enough for the user to see what decision or pattern each one represents.
2. Given a memory entry is being inspected, when the user reviews its details, then they can identify the learned behavior type, such as mapping, categorization, naming, transfer detection, deduplication, clarification outcome, or import handling, and they can see enough context to decide whether the memory should remain in effect.
3. Given stored memory is empty, malformed, schema-incompatible, missing required fields, or contains import-source records discoverable only through the import-source index, when inspection runs, then the workflow reports the condition clearly, continues inspecting other readable memory where possible, and does not mutate `.auto-bean/memory/**`.
4. Given inspection output is produced, when the user reviews it, then the output distinguishes read-only inspection from correction/refinement, points the user to the later explicit correction workflow for changes, and preserves the rule that only the governed memory workflow modifies durable memory.

## Tasks / Subtasks

- [x] Extend the governed memory skill with read-only inspection behavior. (AC: 1, 2, 3, 4)
  - [x] Update `skill_sources/auto-bean-memory/SKILL.md` so it can handle inspection requests as well as approved persistence requests.
  - [x] Keep the inspection path read-only unless the user explicitly invokes an eligible persistence action from the existing governed memory write flow.
  - [x] Require inspection to read `.agents/skills/shared/memory-access-rules.md` before inspecting runtime memory.
  - [x] Make the skill read the fixed governed memory files from `.auto-bean/memory/` and read `.auto-bean/memory/import_sources/index.json` before any import-source memory file.
- [x] Define the inspection presentation contract. (AC: 1, 2, 4)
  - [x] For each readable entry, present memory path, `memory_type`, decision or pattern summary, source context, scope, confidence or review state, audit context, created/updated timestamps, and known reuse limits.
  - [x] Group or label entries by memory category so account mappings, category mappings, naming conventions, transfer decisions, deduplication decisions, clarification outcomes, and import-source behavior are easy to scan.
  - [x] Include enough source and audit context to explain why the memory exists without dumping raw statements, full ledgers, or unrelated financial data.
  - [x] End inspection with a concise read-only summary: files inspected, entries found, unreadable files or records, and whether any entries appear too broad, stale, malformed, or worth reviewing later.
- [x] Handle missing and invalid memory safely. (AC: 3)
  - [x] Treat empty category files as normal and report no stored records for that category.
  - [x] Fail closed on invalid JSON, wrong `memory_type`, missing top-level `records`/`sources`, missing required record fields, index entries pointing outside `.auto-bean/memory/import_sources/`, or source files not listed by the index.
  - [x] Continue inspecting independent categories when one file is unreadable, while clearly reporting the skipped file and reason.
  - [x] Do not infer or repair memory during inspection; repair/correction belongs to Story 4.4.
- [x] Preserve workflow boundaries and product-repo structure. (AC: 3, 4)
  - [x] Author behavior in `skill_sources/` first and do not add live installed runtime skills under product-repo `.agents/skills/`.
  - [x] Do not add a Python memory service, database, vector store, YAML memory format, or new persistent cache for this story.
  - [x] Do not modify `workspace_template/.auto-bean/memory/**` unless the fixed skeleton contract itself must change.
  - [x] Do not add correction, deletion, merge, approval, or migration behavior; Story 4.4 owns explicit memory changes.
- [x] Run validation. (AC: 1, 2, 3, 4)
  - [x] Run `uv run ruff check` and `uv run ruff format`.
  - [x] Run `uv run mypy` if Python code or tests change.
  - [x] Run `uv run pytest`.

## Dev Notes

- Story 4.3 builds on the actual implemented Epic 4 contract: governed memory is deterministic JSON under `.auto-bean/memory/`, owned by the `auto-bean-memory` skill and shared memory access rules. Do not resurrect the older unused Python memory service or Pydantic dependency removed during Story 4.1 review.
- This story is inspection-only. It should help a user understand what learned memory may influence future workflows; it should not correct, refine, delete, merge, migrate, or rewrite memory records. Story 4.4 owns explicit correction/refinement.
- The product repo is not a live user ledger workspace. Author behavior in `skill_sources/` first, install authored skills during `auto-bean init`, and do not add live runtime skills under product-repo `.agents/skills/`.
- Inspection is a trust UX surface. The output should be concise, attributable, and understandable, with enough context to decide whether memory should remain in effect without exposing unnecessary raw financial data.
- Memory records remain advisory. Inspection should describe future influence potential, but it must not imply that memory overrides current evidence, ledger validation, clarification, finding review, or commit/push approval.

### Technical Requirements

- Use the fixed governed memory files:
  - `.auto-bean/memory/account_mappings.json`
  - `.auto-bean/memory/category_mappings.json`
  - `.auto-bean/memory/naming_conventions.json`
  - `.auto-bean/memory/transfer_detection.json`
  - `.auto-bean/memory/deduplication_decisions.json`
  - `.auto-bean/memory/clarification_outcomes.json`
  - `.auto-bean/memory/import_sources/index.json`
  - `.auto-bean/memory/import_sources/<source_slug>.json`
- For non-import-source categories, inspect top-level `memory_type`, and `records`.
- For import-source behavior, inspect `.auto-bean/memory/import_sources/index.json` first, then only source files referenced by valid index entries under `.auto-bean/memory/import_sources/`.
- Required inspectable record fields `memory_type`, `source`, `decision`, `scope`, `confidence` or `review_state`, `created_at`, `updated_at`, and `audit`.
- Inspection output should summarize each record in user-facing terms: what behavior was learned, where it came from, where it applies, how confident or reviewed it is, when it was last updated, and what future workflow it may affect.
- Report malformed or unsafe memory explicitly and read-only. Do not auto-normalize, rewrite, delete, or create memory files during inspection.
- No new external dependency is expected.

### Architecture Compliance

- Architecture requires durable operational memory to live under `.auto-bean/memory/`, local and versionable, with user-owned memory preserved across product upgrades.
- Architecture identifies memory inspection and correction as owned by `.agents/skills/auto-bean-memory/` and shared memory policy, not by import/apply/query/write workflows.
- Authority boundaries remain intact: only the memory skill may modify `.auto-bean/memory/**`; query workflows are read-only; ledger mutation workflows still require validation, review, approval, and auditability.
- The implemented Story 4.1/4.2 contract intentionally favors authored skill guidance and deterministic asset tests over a Python memory package. Follow that current codebase pattern.

### Library / Framework Requirements

- Use the existing Python 3.13, Click, Rich, Ruff, mypy, pytest, Beancount, and Fava baseline.
- Prefer authored markdown workflow and asset-test changes. Add Python support code only if a concrete caller needs reusable logic that cannot be expressed safely in skill guidance.
- If Python tests are added or changed, keep them deterministic and focused on authored memory assets and workflow guardrails.
- Do not introduce Pydantic, YAML, a database, vector search, or a persistent cache for inspection.

### File Structure Requirements

- Likely files to modify:
  - `skill_sources/auto-bean-memory/SKILL.md`
  - `skill_sources/shared/memory-access-rules.md` only if shared inspection rules need central wording
  - `tests/test_memory_assets.py` or a focused new test file under `tests/`
- Likely files to inspect but not necessarily modify:
  - `workspace_template/.auto-bean/memory/*.json`
  - `workspace_template/.auto-bean/memory/import_sources/index.json`
  - `skill_sources/auto-bean-memory/references/*.example.md`
- Do not modify product-repo `.agents/skills/`.
- Do not change initialized workspace skeleton memory files unless a test or guidance update proves the fixed file contract is incomplete.

### Testing Requirements

- Run `uv run ruff check` and `uv run ruff format` after changes.
- Run `uv run mypy` if Python code or tests change.
- Run `uv run pytest`.

### Previous Story Intelligence

- Story 4.1 created the governed memory foundation as authored skill behavior plus deterministic JSON skeleton files, then removed an unused Python memory package and Pydantic dependency after review feedback.
- Story 4.1 established exact memory destinations, `schema_version: 1`, matching `memory_type`, deterministic JSON with two-space indentation and trailing newline, and no path escapes outside `.auto-bean/memory/`.
- Story 4.2 made memory reuse advisory, attributable, and bounded by current evidence. It updated import/apply/write/query guidance so memory influence is visible in review surfaces but does not become silent authority.
- The latest relevant commit is `ecb96cf story 4.2`, which modified the Story 4.2 file, sprint status, import/apply/query/write skill guidance, and shared memory access rules.

### Git Intelligence

- Recent commits:
  - `ecb96cf story 4.2`
  - `9654ca2 story 4.1`
  - `d5f7ff6 update`
  - `8bdc79a update skills`
  - `8bc6fa3 improve cli and init`
- The working tree was clean before creating this story file.
- Prior Epic 4 implementation has favored small authored skill changes plus deterministic asset tests rather than adding new runtime services.

### Latest Technical Information

- No external library upgrade or new external API is required for Story 4.3. The relevant implementation surface is local authored skill behavior, deterministic JSON, and existing pytest-based asset tests.
- If implementation makes authoritative Beancount syntax, balancing, metadata, or account-constraint claims, consult Beancount documentation through Context7 first. This inspection story should not need those claims.

### Project Structure Notes

- No separate UX artifact or `project-context.md` was found. Interaction requirements come from the PRD, Epic 4, architecture, Story 4.1, Story 4.2, current memory skill sources, and tests.
- Review/inspection text is the product UX here. Make it clear enough for a user to decide whether a memory entry deserves later correction while keeping this story read-only.
- Keep the implementation narrow: memory inspection guidance and tests, not a new CLI-first workflow.

### References

- [Epic breakdown](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/epics.md)
- [PRD](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/prd.md)
- [Architecture](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/architecture.md)
- [Sprint status](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/sprint-status.yaml)
- [Story 4.1](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/4-1-persist-governed-memory-for-mappings-categorization-naming-and-import-behavior.md)
- [Story 4.2](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/4-2-reuse-learned-memory-in-future-import-and-reconciliation-workflows.md)
- [Memory skill source](/Users/sam/Projects/auto-bean/skill_sources/auto-bean-memory/SKILL.md)
- [Memory access rules](/Users/sam/Projects/auto-bean/skill_sources/shared/memory-access-rules.md)
- [Workspace template memory root](/Users/sam/Projects/auto-bean/workspace_template/.auto-bean/memory)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story 4.3 created on 2026-04-24 from current `sprint-status.yaml`, `epics.md`, `prd.md`, `architecture.md`, Story 4.1, Story 4.2, current memory skill source, shared memory access rules, workspace template memory skeleton, deterministic memory asset tests, and recent git history.
- No separate UX artifact or `project-context.md` was available.
- No external library research was needed because this story requires no new dependency or external API.
- 2026-04-24: Added red tests for read-only memory inspection and presentation contract; confirmed targeted test failure before implementation.
- 2026-04-24: Updated authored `auto-bean-memory` skill source and UI metadata for read-only inspection while preserving the governed persistence flow.
- 2026-04-24: Ran `uv run pytest tests/test_memory_assets.py -q` after implementation; 10 tests passed.
- 2026-04-24: Ran `uv run ruff check`, `uv run ruff format`, `uv run mypy`, and `uv run pytest`; all passed.

### Completion Notes List

- Selected the first backlog story in sprint order: `4-3-inspect-stored-memory-that-influences-future-behavior`.
- Created a ready-for-dev story focused on read-only governed memory inspection, reviewable memory summaries, malformed-memory reporting, index-first import-source inspection, and preservation of correction boundaries for Story 4.4.
- Scoped implementation toward authored skill-source changes and deterministic tests, consistent with Story 4.1 and Story 4.2.
- Added a read-only inspection workflow to `auto-bean-memory`, covering fixed memory files, import-source index-first reads, category labels, required entry fields, malformed-memory reporting, and explicit correction boundaries.
- Added deterministic asset tests that lock the inspection trigger, fail-closed guardrails, import-source safety checks, and presentation summary fields.
- Completed validation with Ruff, mypy, and pytest passing; story is ready for review.

### File List

- _bmad-output/implementation-artifacts/4-3-inspect-stored-memory-that-influences-future-behavior.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- skill_sources/auto-bean-memory/SKILL.md
- skill_sources/auto-bean-memory/agents/openai.yaml
- tests/test_memory_assets.py

### Change Log

- 2026-04-24: Created Story 4.3 memory inspection context and moved the story to ready-for-dev.
- 2026-04-24: Implemented read-only governed memory inspection guidance and deterministic asset tests for the inspection contract.
- 2026-04-24: Completed validation and moved Story 4.3 to review.
