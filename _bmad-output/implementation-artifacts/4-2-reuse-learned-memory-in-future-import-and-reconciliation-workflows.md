# Story 4.2: Reuse learned memory in future import and reconciliation workflows

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a repeat user,
I want prior decisions reused in later workflows,
so that repeated imports and categorizations require less manual correction.

## Acceptance Criteria

1. Given relevant governed memory exists from prior approved workflows, when a new import or reconciliation run begins, then the system can reuse applicable prior mappings, categorizations, naming conventions, transfer or duplicate decisions, clarification outcomes, or import behaviors and reused memory reduces repetitive setup or correction work.
2. Given reused memory affects a current proposal, when the proposal is presented for review, then the memory influence is attributable and reviewable and the system does not silently conceal that past decisions shaped the outcome.
3. Given governed memory is missing, malformed, stale, too broad, or does not match the current evidence, when an import or reconciliation workflow runs, then the workflow falls back to current evidence, ledger analysis, and bounded clarification rather than forcing a memory-driven result.
4. Given memory reuse is implemented for MVP, when the implementation is inspected, then non-memory workflows only read governed memory as advisory context and still do not write `.auto-bean/memory/**` directly.

## Tasks / Subtasks

- [x] Tighten the shared memory reuse contract. (AC: 1, 2, 3, 4)
  - [x] Update `skill_sources/shared/memory-access-rules.md` so it distinguishes durable memory writes from advisory memory reads.
  - [x] Define required reuse behavior: read fixed governed JSON files, validate the expected top-level shape, treat records as advisory, and fail closed on unclear or unsafe matches.
  - [x] Require every memory-influenced decision to carry enough attribution for the final review surface: memory path, `memory_type`, record identity or stable summary, matched current evidence, decision influenced, and limits on reuse.
- [x] Make import workflow memory reuse deterministic and reviewable. (AC: 1, 2, 3)
  - [x] Update `skill_sources/auto-bean-import/SKILL.md` to read `.auto-bean/memory/import_sources/index.json` first when looking for import-source behavior.
  - [x] Only read the matched `.auto-bean/memory/import_sources/<source_slug>.json` when the index matches current source identity, institution, account hints, statement shape, or source fingerprint.
  - [x] Keep first-seen account-structure inference anchored in current parsed statement evidence and current ledger state; memory may supply hints, not authority.
  - [x] Add import review output requirements that list any reused memory and explain how it affected parsing, source handling, or account-structure suggestions.
- [x] Make apply/reconciliation memory reuse explicit before transaction drafting. (AC: 1, 2, 3)
  - [x] Update `skill_sources/auto-bean-apply/SKILL.md` so categorization and reconciliation consistently check the fixed memory files that match the current work: category mappings, account mappings, naming conventions, transfer detection, deduplication decisions, clarification outcomes, and matched import-source behavior.
  - [x] Require match checks against current parsed statement facts, current ledger context, account constraints, and reconciliation evidence before passing a memory-derived suggestion to `$auto-bean-write`.
  - [x] Require a concise memory-attribution section in the apply review package whenever memory changes a category, posting account suggestion, payee/narration normalization, transfer finding, duplicate finding, or clarification shortcut.
  - [x] If no reliable memory matches, require concrete evidence-based suggestions and bounded clarification rather than vague deferral.
- [x] Keep transaction writing and query boundaries intact. (AC: 2, 3, 4)
  - [x] Update `skill_sources/auto-bean-write/SKILL.md` only if needed to preserve the boundary that write receives categorized evidence or suggestions, verifies ledger context, and does not independently treat memory as authority.
  - [x] Update `skill_sources/auto-bean-query/SKILL.md` only if needed to clarify that query remains read-only and may help verify memory reuse against ledger facts.
  - [x] Do not introduce direct memory writes into import, apply, query, or write workflows.
- [x] Run validation for the changed artifacts. (AC: 1, 2, 3, 4)
  - [x] Run `uv run ruff check` and `uv run ruff format`.
  - [x] Run `uv run mypy` if Python tests or support code changed.
  - [x] Run `uv run pytest`.

## Dev Notes

- Story 4.2 builds on Story 4.1's implemented foundation. That prior story intentionally removed the unused Python memory package and Pydantic dependency after review feedback; MVP memory is governed by authored skill guidance, fixed JSON files in the user workspace, and deterministic asset tests.
- The product repo is not a live user ledger workspace. Author behavior in `skill_sources/` first, install authored skills during `auto-bean init`, and do not add live runtime skills under product-repo `.agents/skills/`.
- This story is about reuse and attribution, not about creating new memory categories, changing the memory persistence workflow, or building rich inspection/correction UX. Stories 4.3 and 4.4 own inspection and correction.
- Memory reuse must improve efficiency without hidden prompt drift. Every reused memory influence must remain advisory, attributable, reviewable, and subordinate to current evidence, ledger validation, clarification, and commit/push approval.
- Current `auto-bean-import` already scans source-context memory hints early, and current `auto-bean-apply` already has a first pass at reading fixed memory files before categorization. This story should harden those behaviors into an explicit, tested contract rather than inventing a parallel mechanism.

### Technical Requirements

- Use the fixed governed memory files created by Story 4.1:
  - `.auto-bean/memory/account_mappings.json`
  - `.auto-bean/memory/category_mappings.json`
  - `.auto-bean/memory/naming_conventions.json`
  - `.auto-bean/memory/transfer_detection.json`
  - `.auto-bean/memory/deduplication_decisions.json`
  - `.auto-bean/memory/clarification_outcomes.json`
  - `.auto-bean/memory/import_sources/index.json`
  - `.auto-bean/memory/import_sources/<source_slug>.json`
- Treat memory records as advisory matching hints. A memory record may influence a proposal only after the workflow compares it with current parsed statement facts, current ledger state, account constraints, and reconciliation evidence relevant to the decision.
- Require stable review attribution for every memory-influenced proposal. At minimum include the source file path, memory type, matched source or record summary, current evidence that matched it, resulting suggestion, and any confidence or scope limits.
- Fail closed when memory cannot be parsed, has the wrong `schema_version`, has the wrong `memory_type`, lacks `records` or required record fields, conflicts with current evidence, or is too broad for the current statement or transaction.
- Keep non-memory workflows read-only against `.auto-bean/memory/**`. They may read governed memory and may hand eligible persistence requests to `$auto-bean-memory` only after a trustworthy finalized result.
- Do not create a database, vector store, persistent cache, new memory service, YAML memory format, or broad semantic retrieval layer for MVP.

### Architecture Compliance

- Architecture requires file-backed MVP memory under `.auto-bean/memory/`, local and versionable, with future migration deferred.
- Architecture treats memory governance as universal: learned behavior may improve efficiency but must remain inspectable, correctable, and bounded.
- Runtime authority boundaries say only the memory skill may modify `.auto-bean/memory/**`; import and recovery may write artifacts, query is read-only, and ledger mutations remain subject to validation and approval.
- Data flow remains: raw statements under `statements/raw/`, normalized parse outputs under `statements/parsed/`, parsed records into account inference/reconciliation, validated results into review/approval, and learned outcomes into governed memory through approved memory update paths.
- Naming stays `snake_case` for memory keys, Python payloads, and internal contracts.

### Library / Framework Requirements

- Use the existing Python 3.13, Click, Rich, Ruff, mypy, pytest, Beancount, and Fava baseline.
- Prefer authored markdown workflow and asset-test changes. Add Python support code only if a concrete caller needs reusable logic that cannot be expressed safely in skill guidance.
- If Python code is added, keep CLI surfaces thin and support-oriented, use structured outputs at service boundaries, and keep modules cohesive.
- No new external dependency is expected for this story.

### File Structure Requirements

- Likely files to modify:
  - `skill_sources/shared/memory-access-rules.md`
  - `skill_sources/auto-bean-import/SKILL.md`
  - `skill_sources/auto-bean-apply/SKILL.md`
  - `skill_sources/auto-bean-write/SKILL.md` if boundary clarification is needed
  - `skill_sources/auto-bean-query/SKILL.md` if read-only verification clarification is needed
- Do not modify `workspace_template/.auto-bean/memory/**` unless the fixed skeleton contract itself must change; Story 4.2 should consume the skeleton created by Story 4.1.
- Do not add product runtime skills under `/Users/sam/Projects/auto-bean/.agents/skills/`.
- Do not add `src/auto_bean/memory/` just to satisfy the older architecture example; the current implemented contract is skill-governed JSON and tests.

### Testing Requirements

- Run `uv run ruff check` and `uv run ruff format` after changes.
- Run `uv run mypy` if changing Python code or tests.
- Run `uv run pytest`.
- Add focused tests for:
  - import/apply guidance reading fixed governed memory locations
  - import-source behavior going through `import_sources/index.json`
  - memory attribution in review surfaces when memory influences a proposal
  - memory staying advisory and subordinate to current evidence, validation, clarification, and approval
  - absence of direct memory-write authority in non-memory skills

### Previous Story Intelligence

- Story 4.1 created `skill_sources/auto-bean-memory/SKILL.md`, `skill_sources/shared/memory-access-rules.md`, category-specific example references, fixed empty JSON files in `workspace_template/.auto-bean/memory/`, init materialization coverage, README/workspace guidance, smoke support, and deterministic memory asset tests.
- Story 4.1's review cycle removed an unused Python memory package and Pydantic dependency. Do not reintroduce that abstraction unless this story adds a real Python caller with clear value.
- Story 4.1 established exact destinations and manual validation requirements: `schema_version: 1`, matching `memory_type`, deterministic JSON with two-space indentation and trailing newline, and no path escapes outside `.auto-bean/memory/`.
- Existing `auto-bean-import` already includes advisory source-context memory scanning in step 3, but it is loose. This story should make index-first source matching and attribution explicit.
- Existing `auto-bean-apply` already checks fixed memory files before transaction drafting and records matched memory for `$auto-bean-write`; this story should make it comprehensive, testable, and visible in the review package.

### Git Intelligence

- Recent commit `9654ca2 story 4.1` completed the governed memory foundation and is directly relevant to this story.
- Earlier commits include `d5f7ff6 update`, `8bdc79a update skills`, `8bc6fa3 improve cli and init`, and `7bf9ec3 query and write skills`.
- The current working tree was clean before this story file was created.
- Current tests are concentrated in `tests/test_memory_assets.py`, with prior generated `__pycache__` files present but not source artifacts to edit.

### Latest Technical Information

- No external library upgrade or new external API is required for Story 4.2. The relevant implementation surface is local authored skill behavior, deterministic JSON, and existing pytest-based asset tests.
- If implementation touches Beancount transaction-writing guidance, consult Beancount documentation through Context7 before making authoritative assumptions about syntax, balancing, metadata placement, or account constraints.

### Project Structure Notes

- No separate UX artifact or `project-context.md` was found. Interaction requirements come from the PRD, Epic 4, architecture, Story 4.1, and current skill source files.
- The developer should prefer small, direct skill-source edits plus tests. Avoid broad refactors and avoid changing the workspace memory skeleton unless the fixed file contract changes deliberately.
- Review surfaces are the product UX here. Make memory influence visible where import/apply already present parsed facts, inferred edits, reconciliation findings, validation outcome, and finalization boundaries.

### References

- [Epic breakdown](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/epics.md)
- [PRD](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/prd.md)
- [Architecture](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/architecture.md)
- [Sprint status](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/sprint-status.yaml)
- [Story 4.1](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/4-1-persist-governed-memory-for-mappings-categorization-naming-and-import-behavior.md)
- [Memory skill source](/Users/sam/Projects/auto-bean/skill_sources/auto-bean-memory/SKILL.md)
- [Memory access rules](/Users/sam/Projects/auto-bean/skill_sources/shared/memory-access-rules.md)
- [Import skill source](/Users/sam/Projects/auto-bean/skill_sources/auto-bean-import/SKILL.md)
- [Apply skill source](/Users/sam/Projects/auto-bean/skill_sources/auto-bean-apply/SKILL.md)
- [Write skill source](/Users/sam/Projects/auto-bean/skill_sources/auto-bean-write/SKILL.md)
- [Query skill source](/Users/sam/Projects/auto-bean/skill_sources/auto-bean-query/SKILL.md)
- [Workspace template memory root](/Users/sam/Projects/auto-bean/workspace_template/.auto-bean/memory)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story 4.2 created on 2026-04-24 from current `sprint-status.yaml`, `epics.md`, `architecture.md`, Story 4.1, current skill source layout, workspace template memory skeleton, `pyproject.toml`, tests, and recent git history.
- No separate UX artifact or `project-context.md` was available.
- No external library research was needed because this story requires no new dependency; Context7 remains required if implementation makes authoritative Beancount syntax or balancing claims.
- 2026-04-24 15:12 CEST: Added failing memory reuse contract tests in `tests/test_memory_assets.py`, then updated shared/import/apply/write/query authored skill guidance to make governed memory advisory, attributable, and bounded by current evidence.
- 2026-04-24 15:12 CEST: Validation passed with `uv run ruff check`, `uv run ruff format`, `uv run mypy`, and `uv run pytest`.

### Completion Notes List

- Selected the first backlog story in sprint order: `4-2-reuse-learned-memory-in-future-import-and-reconciliation-workflows`.
- Created a ready-for-dev story focused on advisory memory reuse, deterministic matching, proposal attribution, and preservation of memory-write authority boundaries.
- Scoped persistence, inspection, correction, and tuning behaviors to their owning workflows and later Epic 4 stories.
- Implemented the shared memory reuse contract with separate durable-write and advisory-read guidance, required JSON shape validation, fail-closed behavior, and review attribution fields.
- Hardened import and apply workflows so governed memory is read from fixed files, import-source behavior goes through `import_sources/index.json`, memory remains subordinate to current evidence, and review packages expose memory influence.
- Clarified write/query boundaries so write verifies memory-derived suggestions without treating memory as authority, query remains read-only, and no non-memory skill gains direct memory-write authority.
- Added deterministic asset tests for the Story 4.2 reuse and attribution contract.

### File List

- _bmad-output/implementation-artifacts/4-2-reuse-learned-memory-in-future-import-and-reconciliation-workflows.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- skill_sources/shared/memory-access-rules.md
- skill_sources/auto-bean-import/SKILL.md
- skill_sources/auto-bean-apply/SKILL.md
- skill_sources/auto-bean-write/SKILL.md
- skill_sources/auto-bean-query/SKILL.md
- tests/test_memory_assets.py

### Change Log

- 2026-04-24: Implemented Story 4.2 memory reuse guidance and tests; story moved to review.
