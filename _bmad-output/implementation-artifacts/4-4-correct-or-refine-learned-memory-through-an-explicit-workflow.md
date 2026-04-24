# Story 4.4: Correct or refine learned memory through an explicit workflow

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user whose past decisions may no longer be desired,
I want to correct or refine learned memory explicitly,
so that future behavior improves instead of repeating outdated assumptions.

## Acceptance Criteria

1. Given an existing memory entry is wrong, outdated, or too broad, when the user invokes the memory correction workflow, then the system allows that memory to be corrected, refined, or removed through an explicit governed path and the change is treated as a controlled update rather than an opaque side effect.
2. Given a memory correction has been made, when a later workflow relies on the affected memory type, then the corrected memory influences future proposals instead of the superseded behavior and the user can inspect that the update took effect.
3. Given a correction request targets missing, malformed, schema-incompatible, ambiguous, unlisted import-source, or path-unsafe memory, when the workflow evaluates the request, then it fails closed with a clear explanation and does not partially rewrite unrelated memory.
4. Given a correction, refinement, or removal is completed, when the workflow reports the result, then it presents the exact memory path changed, affected record identity or stable summary, before/after behavior, audit context, and future reuse limits without dumping raw statements, full ledgers, or unrelated financial data.

## Tasks / Subtasks

- [x] Extend the governed memory skill with explicit correction/refinement behavior. (AC: 1, 3, 4)
  - [x] Update `skill_sources/auto-bean-memory/SKILL.md` so it has a separate correction path alongside read-only inspection and governed persistence.
  - [x] Require the correction path to read `.agents/skills/shared/memory-access-rules.md` before touching runtime memory.
  - [x] Keep correction/refinement/removal inside the memory workflow only; do not grant import, apply, query, write, or recovery direct write authority to `.auto-bean/memory/**`.
  - [x] Require the user to identify the target record through a memory path plus stable record summary, source context, or previous inspection output before a write can happen.
- [x] Define controlled update semantics for all fixed memory categories. (AC: 1, 2, 3)
  - [x] Support correction or refinement of records in `account_mappings.json`, `category_mappings.json`, `naming_conventions.json`, `transfer_detection.json`, `deduplication_decisions.json`, `clarification_outcomes.json`, and indexed `import_sources/<source_slug>.json`.
  - [x] Support removal by deleting the targeted record from its `records` list while preserving the category file shape, unrelated records, `schema_version`, and `memory_type`.
  - [x] For import-source behavior, read and validate `import_sources/index.json` first and only edit source files referenced by valid index entries under `.auto-bean/memory/import_sources/`.
  - [x] If an import-source file loses all records, define whether to keep the empty source file and index entry or remove/update both; choose one deterministic behavior and test it.
- [x] Add fail-closed validation before any memory rewrite. (AC: 1, 3)
  - [x] Reject missing files, invalid JSON, wrong `schema_version`, wrong `memory_type`, missing top-level `records`/`sources`, missing required record fields, path escapes, duplicate target matches, and correction requests that do not identify exactly one record.
  - [x] Validate the updated record still has `schema_version`, `memory_type`, `source`, `decision`, `scope`, `confidence` or `review_state`, `created_at`, `updated_at`, and `audit`.
  - [x] Preserve deterministic JSON with two-space indentation and a trailing newline.
  - [x] Preserve unrelated records byte-for-byte where practical at the data level; do not reorder unrelated records unless the existing project formatting path requires it.
- [x] Make correction review output inspectable and attributable. (AC: 2, 4)
  - [x] Present a concise before/after summary for corrected or refined behavior, including memory path, memory type, target record summary, source context, scope, confidence or review state, audit context, and future reuse limits.
  - [x] Present removals as controlled memory changes, not silent deletion; include why the record was removed and what future workflows should no longer infer from it.
  - [x] Tell the user how to inspect the changed memory afterward through the Story 4.3 inspection path.
  - [x] Avoid printing raw financial statements, full ledger excerpts, or unrelated records in correction output.
- [x] Preserve future workflow behavior and authority boundaries. (AC: 2, 3)
  - [x] Ensure existing advisory memory reuse rules will naturally prefer the corrected record or absence of a removed record in later import/apply workflows.
  - [x] Do not add a database, vector store, persistent cache, broad semantic retrieval layer, YAML memory format, or unused Python memory service.
  - [x] Do not modify `workspace_template/.auto-bean/memory/**` unless the fixed skeleton contract must change.
  - [x] Do not add live installed runtime skills under product-repo `.agents/skills/`.

## Dev Notes

- Story 4.4 builds directly on the implemented Story 4.1-4.3 memory contract: governed memory is deterministic JSON under `.auto-bean/memory/`, owned by the `auto-bean-memory` skill and shared memory access rules.
- This story is explicit memory correction/refinement/removal. It should not broaden into feedback tuning, automatic learning loops, or hidden prompt drift; Story 4.5 owns supervised behavior tuning over time.
- The product repo is not a live user ledger workspace. Author behavior in `skill_sources/` first, install authored skills during `auto-bean init`, and do not add runtime copies under product-repo `.agents/skills/`.
- The correction workflow is a trust UX surface. It must be deliberate, attributable, and easy to inspect afterward. Treat every rewrite of `.auto-bean/memory/**` as governed operational state, not a convenience edit.
- Current memory remains advisory. Corrected memory may influence later proposals, but it still cannot override current evidence, ledger validation, clarification, finding review, or commit/push approval.

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
- For import-source behavior, validate `.auto-bean/memory/import_sources/index.json` before reading or editing any source file. Edit only files referenced by valid index entries whose paths stay inside `.auto-bean/memory/import_sources/`.
- Correction must identify exactly one target record. If zero or multiple records match, ask for clarification instead of guessing.
- Updated records must preserve required fields:  `memory_type`, `source`, `decision`, `scope`, `confidence` or `review_state`, `created_at`, `updated_at`, and `audit`.
- For refinements, narrow scope or improve decision details without erasing audit history. Update `updated_at` and add audit context explaining the correction request.
- For removals, delete only the targeted record and report the controlled removal. Do not delete category files or unrelated records.
- No new external dependency is expected.

### Architecture Compliance

- Architecture requires durable operational memory to live under `.auto-bean/memory/`, local and versionable, with user-owned memory preserved across product upgrades.
- Runtime authority boundaries say only the memory skill may modify `.auto-bean/memory/**`; query remains read-only, and import/apply/write workflows may only read memory as advisory context or request governed persistence.
- Architecture treats memory governance as universal: learned behavior may improve efficiency but must remain inspectable, correctable, bounded, and subordinate to current evidence.
- The implemented Epic 4 pattern intentionally favors authored skill guidance and deterministic asset tests over an unused Python memory package. Continue that pattern unless a concrete support-code caller proves otherwise.

### Library / Framework Requirements

- Use the existing Python 3.13, Click, Rich, Ruff, mypy, pytest, Beancount, and Fava baseline.
- Prefer authored markdown workflow and asset-test changes. Add Python support code only if correction logic needs reusable deterministic helpers that cannot be safely expressed in skill guidance.
- If Python tests are added or changed, keep them deterministic and focused on authored memory assets and workflow guardrails.
- Do not introduce Pydantic, YAML, a database, vector search, or a persistent cache for this correction story.

### File Structure Requirements

- Likely files to modify:
  - `skill_sources/auto-bean-memory/SKILL.md`
  - `skill_sources/shared/memory-access-rules.md` only if shared correction rules belong beside cross-skill memory policy
  - `tests/test_memory_assets.py`
- Likely files to inspect but not necessarily modify:
  - `workspace_template/.auto-bean/memory/*.json`
  - `workspace_template/.auto-bean/memory/import_sources/index.json`
  - `skill_sources/auto-bean-memory/references/*.example.md`
  - `skill_sources/auto-bean-import/SKILL.md`
  - `skill_sources/auto-bean-apply/SKILL.md`
  - `skill_sources/auto-bean-query/SKILL.md`
  - `skill_sources/auto-bean-write/SKILL.md`
- Do not modify product-repo `.agents/skills/`.
- Do not change initialized workspace skeleton memory files unless the fixed file contract itself must change.

### Testing Requirements

- Run `uv run ruff check` and `uv run ruff format` after changes.
- Run `uv run mypy` if Python code or tests change.
- Run `uv run pytest`.
- Add focused tests for:
  - memory correction/refinement/removal trigger language in `auto-bean-memory`
  - correction path staying separate from inspection and persistence paths
  - exact fixed governed memory destinations and import-source index-first behavior
  - single-record target requirement and fail-closed behavior for ambiguous matches
  - missing/malformed/schema-incompatible/path-unsafe memory rejection
  - review output requirements for path, target summary, before/after behavior, audit context, and future reuse limits
  - no direct memory-write authority in non-memory skills

### Previous Story Intelligence

- Story 4.1 created the governed memory foundation as authored skill behavior plus deterministic JSON skeleton files, then removed an unused Python memory package and Pydantic dependency after review feedback.
- Story 4.1 established exact memory destinations, `schema_version: 1`, matching `memory_type`, deterministic JSON with two-space indentation and trailing newline, and no path escapes outside `.auto-bean/memory/`.
- Story 4.2 made memory reuse advisory, attributable, and bounded by current evidence. It updated import/apply/write/query guidance so memory influence is visible in review surfaces but does not become silent authority.
- Story 4.3 added read-only memory inspection and explicitly deferred correction, deletion, merge, approval, and migration behavior to Story 4.4.
- Current `auto-bean-memory` already has separate read-only inspection and governed persistence sections. Story 4.4 should add a third explicit correction/refinement/removal section rather than overloading either existing path.

### Git Intelligence

- Recent commits:
  - `25f8e16 story 4.3`
  - `ecb96cf story 4.2`
  - `9654ca2 story 4.1`
  - `d5f7ff6 update`
  - `8bdc79a update skills`
- The working tree was clean before creating this story file.

### Latest Technical Information

- No external library upgrade or new external API is required for Story 4.4. The relevant implementation surface is local authored skill behavior, deterministic JSON, and existing pytest-based asset tests.
- If implementation makes authoritative Beancount syntax, balancing, metadata, or account-constraint claims, consult Beancount documentation through Context7 first. This correction story should not need those claims.

### Project Structure Notes

- No separate UX artifact or `project-context.md` was found. Interaction requirements come from the PRD, Epic 4, architecture, Stories 4.1-4.3, current memory skill sources, shared memory access rules, workspace template memory skeleton, and tests.
- Correction output is the product UX here. Make it clear enough for a user to understand exactly what changed, why, and how future workflow behavior is affected.
- Keep the implementation narrow: governed memory correction guidance and tests, not a new CLI-first workflow or general memory migration tool.

### References

- [Epic breakdown](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/epics.md)
- [PRD](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/prd.md)
- [Architecture](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/architecture.md)
- [Sprint status](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/sprint-status.yaml)
- [Story 4.1](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/4-1-persist-governed-memory-for-mappings-categorization-naming-and-import-behavior.md)
- [Story 4.2](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/4-2-reuse-learned-memory-in-future-import-and-reconciliation-workflows.md)
- [Story 4.3](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/4-3-inspect-stored-memory-that-influences-future-behavior.md)
- [Memory skill source](/Users/sam/Projects/auto-bean/skill_sources/auto-bean-memory/SKILL.md)
- [Memory access rules](/Users/sam/Projects/auto-bean/skill_sources/shared/memory-access-rules.md)
- [Workspace template memory root](/Users/sam/Projects/auto-bean/workspace_template/.auto-bean/memory)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story 4.4 created on 2026-04-24 from current `sprint-status.yaml`, `epics.md`, `prd.md`, `architecture.md`, Stories 4.1-4.3, current memory skill source, shared memory access rules, workspace template memory skeleton, deterministic memory asset tests, and recent git history.
- No separate UX artifact or `project-context.md` was available.
- No external library research was needed because this story requires no new dependency or external API.
- 2026-04-24: Red phase confirmed new correction asset tests failed before implementation (`uv run pytest tests/test_memory_assets.py`: 4 failures).
- 2026-04-24: Implemented explicit correction/refinement/removal workflow in authored memory skill and shared memory access rules.
- 2026-04-24: Verified targeted memory asset tests, lint, formatting, type checks, and full tests pass.

### Completion Notes List

- Selected the first backlog story in sprint order: `4-4-correct-or-refine-learned-memory-through-an-explicit-workflow`.
- Created a ready-for-dev story focused on explicit governed memory correction, refinement, removal, fail-closed validation, reviewable before/after reporting, and preservation of Epic 4 memory authority boundaries.
- Added a third `auto-bean-memory` workflow for explicit correction, refinement, and removal, kept separate from read-only inspection and governed persistence.
- Defined fixed-category and indexed import-source correction semantics, including deterministic retention of empty import-source files and index entries after all records are removed.
- Added fail-closed validation, single-record target requirements, deterministic JSON requirements, and review output requirements for path, target summary, before/after behavior, audit context, future reuse limits, and raw-data redaction.
- Updated shared memory access rules so correction/refinement/removal are explicitly governed memory writes owned by `$auto-bean-memory`.
- Added deterministic asset tests covering correction trigger language, workflow separation, fixed destinations, index-first import-source behavior, fail-closed validation, review output, and non-memory skill authority boundaries.

### File List

- _bmad-output/implementation-artifacts/4-4-correct-or-refine-learned-memory-through-an-explicit-workflow.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- skill_sources/auto-bean-memory/SKILL.md
- skill_sources/shared/memory-access-rules.md
- tests/test_memory_assets.py

### Change Log

- 2026-04-24: Created Story 4.4 memory correction/refinement context and moved the story to ready-for-dev.
- 2026-04-24: Implemented explicit governed memory correction/refinement/removal workflow and moved story to review.
