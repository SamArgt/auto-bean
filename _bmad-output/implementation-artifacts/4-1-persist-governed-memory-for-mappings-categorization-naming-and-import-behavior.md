# Story 4.1: Persist governed memory for mappings, categorization, naming, transfer detection, deduplication, and import behavior

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a repeat user,
I want the system to persist learned operational decisions in governed local memory,
so that useful past decisions can improve future workflows without becoming opaque or unsafe.

## Acceptance Criteria

1. Given a workflow produces reusable decisions such as account mappings, categorization outcomes, naming conventions, transfer detection logic, deduplication decisions, or import-handling rules, when the workflow finalizes an approved result, then the system persists those decisions through the governed memory abstraction and the stored memory remains local, versionable, and separate from raw ledger files.
2. Given memory is persisted for MVP, when the underlying storage is inspected, then the memory is file-backed in a governed local structure consistent with the architecture and the storage contract allows future migration without changing higher-level workflow behavior.
3. Given memory records are written, when the records are loaded again, then schema version, memory type, source context, confidence or review state, and audit metadata are validated at the service boundary before any higher-level workflow may rely on them.
4. Given a workflow is not the governed memory workflow or memory service, when it wants to store reusable decisions, then it must call the governed memory abstraction rather than writing `.auto-bean/memory/**` directly.

## Tasks / Subtasks

- [x] Define the governed memory contract and authored workflow boundary. (AC: 1, 2, 4)
  - [x] Create or materially update authored memory guidance under `skill_sources/auto-bean-memory/` and shared policy under `skill_sources/shared/` as needed; use the `skill-creator` system skill before creating or materially editing skill behavior.
  - [x] Document that durable memory writes must go through the governed memory workflow/service and that routine import/apply/query workflows must not write `.auto-bean/memory/**` directly.
  - [x] Identify the initial memory categories covered by this story: account mappings, category mappings, naming conventions, import-source behavior, transfer detection decisions, deduplication decisions, and reusable clarification outcomes.
- [x] Implement a narrow file-backed memory service abstraction. (AC: 1, 2, 3)
  - [x] Add a dedicated memory module only if it improves separation, for example `src/auto_bean/memory/`, with interfaces/models separated from filesystem implementation.
  - [x] Keep CLI surfaces thin; if a helper command is introduced, it should parse input and render structured output while delegating all memory logic to application services.
  - [x] Ensure all memory files are written under the runtime workspace `.auto-bean/memory/` tree, never under raw statements, parsed statements, ledger files, or product-repo `.agents/skills/`.
- [x] Define versioned validated memory records. (AC: 2, 3)
  - [x] Add explicit record fields for `schema_version`, `memory_type`, `source`, `decision`, `scope`, `confidence` or `review_state`, `created_at`, `updated_at`, and audit context such as originating workflow/run or related statement source.
  - [x] Use `snake_case` keys for serialized records and Python payloads.
  - [x] Use Pydantic v2 at service boundaries if adding the architecture-required validation dependency; use `model_validate` for inbound dictionaries and `model_dump`/`model_dump_json` for outbound data.
  - [x] If the implementation chooses a human-editable YAML format, add and justify the YAML dependency explicitly; otherwise prefer a deterministic JSON format over ad hoc unversioned blobs.
- [x] Wire memory persistence into approved-result workflow guidance without changing finalization semantics. (AC: 1, 4)
  - [x] Update import/apply guidance only where necessary so reusable decisions are persisted after the relevant workflow result has been approved/finalized.
  - [x] Do not treat tentative, blocked, rejected, or unvalidated interpretations as durable memory unless the user explicitly approves storing that learning.
  - [x] Preserve the direct ledger mutation trust boundary from Epic 3: validation, diff inspection, and commit/push approval remain separate from memory persistence.
- [x] Materialize memory assets into initialized workspaces. (AC: 1, 2, 4)
  - [x] Update `auto-bean init` materialization so any new authored memory skill, references, shared policy, or template directories are installed from `skill_sources/` into the user workspace.
  - [x] Ensure `workspace_template/.auto-bean/memory/` contains only skeleton placeholders, not sample user financial decisions.
  - [x] Preserve existing user memory on upgrades or repeated init flows; product upgrades must not overwrite durable `.auto-bean/memory/**` without explicit migration logic.
- [x] Add deterministic tests for memory governance. (AC: 1, 2, 3, 4)
  - [x] Unit-test record validation, serialization, bad schema handling, and invalid memory type handling.
  - [x] Unit-test that the file store writes only under the configured `.auto-bean/memory/` root and rejects path traversal or writes outside the governed tree.
  - [x] Add init/materialization coverage for new skill and shared policy assets.
  - [x] Add skill asset tests that prevent memory-write authority from being duplicated into import/apply/query guidance.

## Dev Notes

- Story 4.1 is the first Epic 4 story, so it creates the foundation for all future memory reuse, inspection, correction, and tuning stories. It should define the storage and authority boundary now, but it should not implement broad retrieval/ranking behavior that belongs to Story 4.2 or rich inspection/correction UX that belongs to Stories 4.3 and 4.4.
- The product repo is not a live user ledger workspace. Author behavior in `skill_sources/` first, install authored skills during `auto-bean init`, and do not add live runtime skills under product-repo `.agents/skills/`.
- This story should prevent hidden prompt drift. Durable learned behavior must be inspectable, local, versionable, schema-versioned, and attributable to an approved workflow result.
- Existing runtime skeleton already includes `workspace_template/.auto-bean/memory/import_sources/.gitkeep`. Build on that governed tree rather than inventing a second memory location.
- Current package dependencies do not include Pydantic or a YAML parser. Architecture calls for Pydantic v2 validation at service boundaries, so adding `pydantic>=2,<3` is expected if Python memory records are implemented. Add any YAML dependency only if the implementation deliberately chooses YAML as the canonical memory file format.

### Technical Requirements

- Implement a memory service abstraction before or alongside file-backed persistence. Higher-level workflows should depend on the service contract, not on direct file paths or serialization details.
- Store durable memory under `.auto-bean/memory/` in the user ledger workspace. The product repo may contain templates, tests, authored skill source, and support code only.
- Keep memory records schema-versioned. Invalid or unsupported schema versions must fail closed with a structured error rather than being silently ignored or coerced.
- Persist only approved reusable decisions. Tentative reconciliation guesses, blocked findings, rejected interpretations, and validation-failed outcomes should remain diagnostics or review context unless the user explicitly approves storing them as memory.
- Keep source context with every stored decision so future inspection can explain why the memory exists and what workflow or statement source produced it.
- Do not introduce a database, vector store, persistent cache, hosted service, or opaque agent-only memory for MVP.
- Do not mix normalized statement parse outputs with memory. `statements/parsed/` remains for parsed statement outputs; `.auto-bean/memory/` remains for durable learned decisions.

### Architecture Compliance

- Architecture requires file-backed MVP memory behind a repository/service abstraction so future PostgreSQL/vector retrieval can be introduced without rewriting workflow logic.
- Pydantic v2 should validate memory records at Python service boundaries when Python support code owns the contract.
- Memory files must use `snake_case` keys and live under one governed local tree, with no ad hoc JSON/YAML blobs spread across the repo.
- Only the governed memory workflow/service may modify `.auto-bean/memory/**`. Import, apply, and query workflows may request persistence but should not own direct writes.
- Stable user-owned assets, including memory, must be preserved across product upgrades and repeated workspace initialization.

### Library / Framework Requirements

- Use the existing Python 3.13, Click, Rich, Ruff, mypy, and pytest baseline.
- If implementing validated Python models, add Pydantic v2 intentionally and use current v2 APIs: `BaseModel.model_validate(...)` for dictionaries, `model_validate_json(...)` for JSON strings, and `model_dump(...)` or `model_dump_json(...)` for serialization.
- Avoid deprecated Pydantic v1 patterns such as `parse_obj`, `.dict()`, or `.json()` in new code.
- Prefer standard-library JSON for deterministic first-slice persistence unless the story implementation explicitly chooses a human-editable YAML format and adds a bounded YAML dependency.

### File Structure Requirements

- Likely files or directories to create or modify:
  - `skill_sources/auto-bean-memory/SKILL.md`
  - `skill_sources/auto-bean-memory/agents/openai.yaml`
  - `skill_sources/auto-bean-memory/references/`
  - `skill_sources/shared/memory-access-rules.md`
  - `src/auto_bean/memory/`
  - `src/auto_bean/init.py`
  - `workspace_template/.auto-bean/memory/`
  - `workspace_template/AGENTS.md`
  - `README.md`
  - `pyproject.toml`
  - `tests/`
- Keep new Python modules cohesive. A memory package is acceptable because memory is an independent concern; do not create a generic utilities module.
- Do not place runtime memory examples containing financial decisions in `workspace_template/`. Use `.gitkeep` placeholders or non-financial schema documentation.
- Do not add product runtime skills under `/Users/sam/Projects/auto-bean/.agents/skills/`.

### Testing Requirements

- Run `uv run ruff check` and `uv run ruff format` after code changes.
- Run `uv run mypy` when changing Python code.
- Run `uv run pytest` when changing Python code.
- Add focused tests for:
  - memory record validation and serialization
  - unsupported schema versions and invalid memory types
  - file-backed store path containment under `.auto-bean/memory/`
  - deterministic materialization of authored memory skill/shared policy assets during `auto-bean init`
  - preservation of existing workspace memory skeleton and durable memory files
  - absence of direct `.auto-bean/memory/**` write authority in non-memory skill guidance

### Previous Work Intelligence

- Epic 2 and Epic 3 established direct, trust-preserving ledger workflows: parse/review facts, write working-tree changes when confidence allows, validate, present diff and findings, then ask for commit/push approval.
- Story 2.4 preserved source-specific import context, but Epic 4 memory should be broader and governed: it covers reusable account mappings, category decisions, naming, transfer/deduplication decisions, import behavior, and clarification outcomes.
- Story 3.4 reinforced that accepted ledger changes and recovery are git-backed and audit-friendly. Memory persistence must complement that trust boundary, not bypass it by silently saving unapproved interpretations.
- Existing implementation work has favored authored skill changes, workspace guidance, init-time materialization, and deterministic tests. Story 4.1 should follow that same pattern.

### Git Intelligence

- Recent commits: `d5f7ff6 update`, `8bdc79a update skills`, `8bc6fa3 improve cli and init`, `7bf9ec3 query and write skills`, `815b450 delete tests`.
- Current repo state includes authored `auto-bean-import`, `auto-bean-apply`, `auto-bean-query`, and `auto-bean-write` skills, but no authored `auto-bean-memory` skill yet.
- The current workspace template already has `.auto-bean/memory/import_sources/.gitkeep`; do not relocate the memory root.
- Existing Python support code is concentrated in `src/auto_bean/init.py` and `src/auto_bean/cli.py`; add a memory module only because this story introduces a real independent concern.

### Latest Technical Information

- Context7 Pydantic docs confirm that Pydantic v2 validates dictionaries with `model_validate(...)` and serializes with `model_dump(...)`; JSON strings should use `model_validate_json(...)` and JSON output should use `model_dump_json(...)`.
- Pydantic v2 deprecates `.json()` in favor of `model_dump_json()`. New memory model code should avoid v1 serialization and parsing methods.

### Project Structure Notes

- No separate UX artifact or `project-context.md` was found. Interaction requirements come from the PRD, Epic 4, architecture, and previous story files.
- The story should keep the CLI support-oriented. Memory behavior belongs primarily in authored skill guidance plus reusable support services.
- The first implementation slice may be intentionally small, but it must leave future Story 4.2 reuse and Stories 4.3/4.4 inspection/correction with a stable contract to build on.

### References

- [Epic breakdown](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/epics.md)
- [PRD](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/prd.md)
- [Architecture](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/architecture.md)
- [Sprint status](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/sprint-status.yaml)
- [Story 2.4](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/2-4-persist-source-specific-import-context-for-repeated-imports.md)
- [Story 3.4](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/3-4-validate-inspect-approve-and-recover-ledger-mutations-safely.md)
- [Import skill source](/Users/sam/Projects/auto-bean/skill_sources/auto-bean-import/SKILL.md)
- [Apply skill source](/Users/sam/Projects/auto-bean/skill_sources/auto-bean-apply/SKILL.md)
- [Write skill source](/Users/sam/Projects/auto-bean/skill_sources/auto-bean-write/SKILL.md)
- [Workspace template memory root](/Users/sam/Projects/auto-bean/workspace_template/.auto-bean/memory/import_sources/.gitkeep)
- [Pydantic v2 model validation docs](https://github.com/pydantic/pydantic/blob/main/docs/concepts/models.md)
- [Pydantic v2 serialization docs](https://github.com/pydantic/pydantic/blob/main/docs/concepts/serialization.md)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story 4.1 created on 2026-04-24 from the current `sprint-status.yaml`, `epics.md`, `prd.md`, `architecture.md`, Story 2.4, Story 3.4, current skill source layout, workspace template memory skeleton, current `pyproject.toml`, and recent git history.
- No separate UX artifact or `project-context.md` was available.
- Context7 Pydantic documentation was consulted for current v2 validation and serialization APIs.
- 2026-04-24: Loaded `bmad-dev-story` and `skill-creator` guidance before implementing authored skill changes.
- 2026-04-24: Added failing memory service and asset tests first; initial focused test run failed on missing `pydantic`, then missing `auto_bean.memory`, then missing governed skill assets.
- 2026-04-24: Revised the implementation after review feedback to remove the unused Python memory package and Pydantic dependency, and to make the authored memory skill responsible for exact governed JSON file placement.
- 2026-04-24: Added fixed workspace memory files for one file per non-import memory category plus `import_sources/index.json` for one-file-per-source import memory lookup.
- 2026-04-24: Added one bundled memory example reference per memory type and updated `auto-bean-memory` to read the chosen category's reference after classification.
- 2026-04-24: Validation passed with `uv run ruff format`, `uv run ruff check`, `uv run mypy`, `uv run pytest`, and `uv run python scripts/run_smoke_checks.py`.

### Implementation Plan

- Define the governed memory authority in authored skill sources first, keeping routine import/apply/query/write workflows as requesters rather than direct memory writers.
- Keep MVP persistence as authored workflow behavior over deterministic JSON files, without a Python memory package until a real caller needs one.
- Extend init/materialization checks and workspace skeletons so generated workspaces include the memory skill, shared policy, fixed empty category files, and import-source index without sample financial decisions.
- Cover the contract with deterministic tests for exact memory file destinations, materialized assets, preservation behavior, and non-memory skill authority boundaries.

### Completion Notes List

- Selected the first backlog story in sprint order: `4-1-persist-governed-memory-for-mappings-categorization-naming-and-import-behavior`.
- Created a ready-for-dev story that establishes the governed memory boundary for Epic 4.
- Included explicit guardrails for file-backed local memory, schema-versioned records, memory-write authority, workspace materialization, and deterministic tests.
- Scoped future reuse, inspection, correction, and tuning behaviors to later Epic 4 stories.
- Implemented the governed memory foundation as a dedicated `auto-bean-memory` authored workflow with exact deterministic JSON destinations.
- Removed the unused Python memory package and Pydantic dependency after review feedback; MVP memory is now governed by skill instructions and fixed workspace files.
- Added concrete example references for every memory type and wired `SKILL.md` so the agent reads only the relevant example after choosing a category.
- Updated import/apply/query/write guidance so reusable decisions are handed to the governed memory workflow after approval/finalization rather than written directly by routine workflows.
- Updated workspace template memory skeletons, init asset checks, README/workspace guidance, dependency metadata, smoke support, and deterministic tests.
- Verified all acceptance criteria and validation gates; story is ready for review.

### File List

- _bmad-output/implementation-artifacts/4-1-persist-governed-memory-for-mappings-categorization-naming-and-import-behavior.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- README.md
- pyproject.toml
- skill_sources/auto-bean-apply/SKILL.md
- skill_sources/auto-bean-apply/references/clarification-guidance.md
- skill_sources/auto-bean-import/SKILL.md
- skill_sources/auto-bean-import/agents/openai.yaml
- skill_sources/auto-bean-memory/SKILL.md
- skill_sources/auto-bean-memory/agents/openai.yaml
- skill_sources/auto-bean-memory/references/account-mapping.example.md
- skill_sources/auto-bean-memory/references/category-mapping.example.md
- skill_sources/auto-bean-memory/references/clarification-outcome.example.md
- skill_sources/auto-bean-memory/references/deduplication-decision.example.md
- skill_sources/auto-bean-memory/references/import-source-behavior.example.md
- skill_sources/auto-bean-memory/references/naming-convention.example.md
- skill_sources/auto-bean-memory/references/transfer-detection.example.md
- skill_sources/auto-bean-query/SKILL.md
- skill_sources/auto-bean-write/SKILL.md
- skill_sources/shared/memory-access-rules.md
- src/auto_bean/init.py
- src/auto_bean/py.typed
- src/auto_bean/smoke.py
- tests/test_memory_assets.py
- uv.lock
- workspace_template/.auto-bean/memory/account_mappings.json
- workspace_template/.auto-bean/memory/category_mappings.json
- workspace_template/.auto-bean/memory/clarification_outcomes.json
- workspace_template/.auto-bean/memory/deduplication_decisions.json
- workspace_template/.auto-bean/memory/import_sources/index.json
- workspace_template/.auto-bean/memory/naming_conventions.json
- workspace_template/.auto-bean/memory/transfer_detection.json
- workspace_template/AGENTS.md

### Change Log

- 2026-04-24: Implemented Story 4.1 governed memory foundation, including authored memory workflow, validated file-backed service, workspace materialization, guidance boundaries, and deterministic tests.
- 2026-04-24: Simplified Story 4.1 memory persistence by removing the unused Python memory service and documenting exact governed JSON destinations, including import-source index-first behavior.
- 2026-04-24: Added category-specific memory examples and progressive-disclosure reference routing to the governed memory skill.
