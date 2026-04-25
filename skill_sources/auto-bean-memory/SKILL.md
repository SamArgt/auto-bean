---
name: auto-bean-memory
description: Inspect governed local memory read-only, correct or refine existing memory through an explicit governed path, or persist approved reusable auto-bean decisions into fixed `.auto-bean/memory/` JSON files with audit context and explicit review boundaries.
---

# Auto Bean Memory

Read this reference before acting:

- `.agents/skills/shared/memory-access-rules.md`

Use this skill when the user asks to inspect, review, list, or explain governed memory, when the user explicitly asks to correct, refine, or remove an existing memory record, or when the user or an approved finalized workflow asks to persist reusable operational learning.

## Read-only inspection workflow

Inspection is read-only. Keep this path separate from persistence unless the user explicitly invokes an eligible persistence action from the governed write flow below.

1. Before inspecting runtime memory, read `.agents/skills/shared/memory-access-rules.md` before inspecting runtime memory and apply its fixed file, advisory-use, and fail-closed rules.
2. Inspect these fixed governed files under `.auto-bean/memory/`:
   - `.auto-bean/memory/account_mappings.json` as Account mappings
   - `.auto-bean/memory/category_mappings.json` as Category mappings
   - `.auto-bean/memory/naming_conventions.json` as Naming conventions
   - `.auto-bean/memory/transfer_detection.json` as Transfer decisions
   - `.auto-bean/memory/deduplication_decisions.json` as Deduplication decisions
   - `.auto-bean/memory/clarification_outcomes.json` as Clarification outcomes
   - `.auto-bean/memory/import_sources/index.json` as Import-source behavior index
3. Read `.auto-bean/memory/import_sources/index.json` before any import-source memory file. For Import-source behavior, read only source files referenced by valid index entries whose relative paths stay inside `.auto-bean/memory/import_sources/`.
4. For non-import-source category files, require top-level `schema_version: 1`, the expected `memory_type`, and a top-level `records` list. Treat empty `records` as normal and report no stored records for that category.
5. For import-source behavior, require the index to contain top-level `schema_version: 1`, `memory_type: import_source_behavior_index`, and a top-level `sources` list. Reject index entries pointing outside `.auto-bean/memory/import_sources/`; reject source files not listed by the index.
6. For each readable record, require `schema_version`, `memory_type`, `source`, `decision`, `scope`, `confidence` or `review_state`, `created_at`, `updated_at`, and `audit`.
7. Fail closed and continue where possible when a file is missing, empty, invalid JSON, schema-incompatible, has the wrong `memory_type`, lacks top-level `records` or `sources`, lacks required record fields, has index entries pointing outside `.auto-bean/memory/import_sources/`, or has source files not listed by the index.
8. Do not infer, repair, normalize, create, update, delete, merge, migrate, or rewrite memory during inspection. Correction and refinement belong to the later explicit correction workflow.
9. Present readable entries grouped or labeled by category: Account mappings, Category mappings, Naming conventions, Transfer decisions, Deduplication decisions, Clarification outcomes, and Import-source behavior.
10. For each readable entry, present:
    - memory path
    - `memory_type`
    - decision or pattern summary
    - source context
    - scope
    - confidence or review state
    - audit context
    - created/updated timestamps
    - known reuse limits
11. Include enough source and audit context to explain why the memory exists without dumping raw statements, full ledgers, or unrelated financial data.
12. End with a concise read-only summary: files inspected, entries found, unreadable files or records, whether any entries appear malformed, stale, too broad, or worth reviewing later, and a reminder that changes require the later explicit correction workflow and that only the governed memory workflow modifies durable memory.

## Explicit correction, refinement, and removal workflow

Keep this path separate from read-only inspection and governed persistence. Use it only when the user explicitly asks to correct, refine, or remove existing governed memory. Do not treat correction as an opaque side effect of import, categorize, query, write, recovery, or general feedback work.

1. First, read `.agents/skills/shared/memory-access-rules.md` before touching runtime memory, then apply its fixed file, advisory-use, fail-closed, and authority-boundary rules.
2. Confirm the request targets one governed memory record and one of these actions:
   - correction: replace a wrong or outdated decision with a more accurate decision
   - refinement: narrow scope, confidence, review state, or decision details without erasing audit history
   - removal: delete a record that should no longer influence future proposals
3. Require the user to identify the target record through a memory path plus stable record summary, source context, or previous inspection output before any write can happen. If the request does not identify exactly one record, ask for clarification and do not rewrite memory.
4. Use only these fixed correction destinations:
   - `.auto-bean/memory/account_mappings.json` for `account_mapping`
   - `.auto-bean/memory/category_mappings.json` for `category_mapping`
   - `.auto-bean/memory/naming_conventions.json` for `naming_convention`
   - `.auto-bean/memory/transfer_detection.json` for `transfer_detection`
   - `.auto-bean/memory/deduplication_decisions.json` for `deduplication_decision`
   - `.auto-bean/memory/clarification_outcomes.json` for `clarification_outcome`
   - `.auto-bean/memory/import_sources/<source_slug>.json` for `import_source_behavior`
5. For import-source behavior, read and validate `.auto-bean/memory/import_sources/index.json` first, and only edit source files referenced by valid index entries whose paths stay inside `.auto-bean/memory/import_sources/`. Reject unlisted source files, path escapes, and ambiguous source matches.
6. If an import-source file loses all records, keep the empty source file and keep its index entry. This deterministic behavior preserves source identity, avoids accidental index churn, and makes later inspection show that the source exists with no reusable records.
7. Before any rewrite, fail closed for:
   - missing files
   - empty or invalid JSON
   - wrong `schema_version`
   - wrong `memory_type`
   - missing top-level `records` or `sources`
   - missing required record fields
   - path escapes outside `.auto-bean/memory/`
   - duplicate target matches
   - zero target matches
   - correction requests that do not identify exactly one record
8. Validate each candidate target record before changing it. Every record must include `schema_version`, `memory_type`, `source`, `decision`, `scope`, `confidence` or `review_state`, `created_at`, `updated_at`, and `audit`.
9. For correction or refinement:
   - update exactly one record in the category file's `records` list
   - preserve `created_at`
   - update `updated_at`
   - preserve or extend `audit` with correction request context, user approval, reason for change, and prior behavior summary
   - validate the updated record still has `schema_version`, `memory_type`, `source`, `decision`, `scope`, `confidence` or `review_state`, `created_at`, `updated_at`, and `audit`
10. For removal:
   - delete only the targeted record from its `records` list
   - preserve the category file shape, unrelated records, `schema_version`, and `memory_type`
   - record in the response why the record was removed and what future workflows should no longer infer from it
11. Preserve deterministic JSON with two-space indentation and a trailing newline. Preserve unrelated records at the data level; do not reorder unrelated records unless the existing formatting path requires it.
12. Present a concise before/after summary for every completed correction or refinement. Include:
   - exact memory path changed
   - memory type
   - target record summary or stable identity
   - source context
   - scope
   - confidence or review state
   - audit context
   - before/after behavior
   - future reuse limits
13. Present removals as a controlled memory change, not silent deletion. Include the memory path, memory type, target record summary, source context, why removal was requested, audit context, and what future workflows should no longer infer.
14. Tell the user how to inspect the changed memory afterward through the Story 4.3 inspection path. Mention that later workflows should prefer the corrected record, refined scope, or absence of a removed record only as advisory context checked against current evidence.
15. Avoid printing raw financial statements, full ledger excerpts, unrelated records, or unrelated financial data in correction output.
16. Do not grant import, categorize, query, write, or recovery direct write authority to `.auto-bean/memory/**`; those workflows may request this governed correction path when memory needs to change.


## Governed persistence workflow

Follow this workflow:

1. Confirm the memory request is eligible:
   - persist only decisions from an approved or finalized result
   - reject tentative, blocked, validation-failed, ambiguous, or deferred interpretations unless the user explicitly approves storing that learning
   - keep raw statements, parsed statement outputs, ledger entries, diagnostics, and proposal artifacts out of memory
2. Classify the memory into one of these categories:
   - `account_mapping`: then read `.agents/skills/auto-bean-memory/references/account-mapping.example.md`
   - `category_mapping`: then read `.agents/skills/auto-bean-memory/references/category-mapping.example.md`
   - `naming_convention`: then read `.agents/skills/auto-bean-memory/references/naming-convention.example.md`
   - `import_source_behavior`: then read `.agents/skills/auto-bean-memory/references/import-source-behavior.example.md`
   - `transfer_detection`: then read `.agents/skills/auto-bean-memory/references/transfer-detection.example.md`
   - `deduplication_decision`: then read `.agents/skills/auto-bean-memory/references/deduplication-decision.example.md`
   - `clarification_outcome`: then read `.agents/skills/auto-bean-memory/references/clarification-outcome.example.md`
   Read only the reference for the chosen category. Use it as the concrete shape example for the record you are about to write.
3. Build a versioned memory record with `snake_case` keys:
   - `schema_version`
   - `memory_type`
   - `source`
   - `decision`
   - `scope`
   - `confidence` or `review_state`
   - `created_at`
   - `updated_at`
   - `audit`
4. Choose the governed memory file from this fixed map:
   - `account_mapping` -> `.auto-bean/memory/account_mappings.json`
   - `category_mapping` -> `.auto-bean/memory/category_mappings.json`
   - `naming_convention` -> `.auto-bean/memory/naming_conventions.json`
   - `transfer_detection` -> `.auto-bean/memory/transfer_detection.json`
   - `deduplication_decision` -> `.auto-bean/memory/deduplication_decisions.json`
   - `clarification_outcome` -> `.auto-bean/memory/clarification_outcomes.json`
   - `import_source_behavior` -> `.auto-bean/memory/import_sources/<source_slug>.json`
5. For non-import-source categories:
   - read the entire category file before editing it
   - keep the top-level shape as `schema_version`, `memory_type`, and `records`
   - append or update exactly one record in `records`
   - preserve unrelated records
6. For `import_source_behavior`:
   - read `.auto-bean/memory/import_sources/index.json` first
   - use the index to find an existing source file when source identity, institution, account, statement shape, or fingerprint matches
   - create a deterministic `<source_slug>.json` only when no existing source file matches
   - update `index.json` whenever a source file is created, renamed, or its lookup metadata changes
   - keep one source file per statement source, with that file containing the source-specific reusable records
7. Validate manually before writing:
   - JSON parses successfully
   - `schema_version` is `1`
   - `memory_type` matches the destination file
   - required record fields are present
   - no path escapes `.auto-bean/memory/`
8. Store deterministic JSON with two-space indentation and a trailing newline.
9. Present a concise review summary:
   - what reusable decision was stored
   - why it is eligible
   - source context and audit context
   - exact memory path written
   - any limits on future reuse

Guardrails:

- Treat memory as advisory context, not silent authority.
- Do not store user financial decisions in installed skill files, templates, or product-repo `.agents/skills/`.
- Do not write `.auto-bean/memory/**` from import, categorize, query, or write workflows directly; those workflows must hand eligible persistence requests to this governed workflow.
- Do not create additional category files, databases, vector stores, caches, YAML files, or ad hoc memory blobs for MVP.
- Do not create broad semantic retrieval layers, persistent caches, or unused support services for memory correction.
- Fail closed when the destination file, record type, source context, approval state, target identity, or storage path is unclear.
