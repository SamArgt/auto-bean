---
name: auto-bean-memory
description: Persist approved reusable auto-bean decisions into governed local memory under the fixed `.auto-bean/memory/` JSON files with audit context and explicit review boundaries.
---

# Auto Bean Memory

Read this reference before acting:

- `.agents/skills/shared/memory-access-rules.md`

Use this skill only when the user or an approved finalized workflow asks to persist reusable operational learning.

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
- Do not write `.auto-bean/memory/**` from import, apply, query, or write workflows directly; those workflows must hand eligible persistence requests to this governed workflow.
- Do not create additional category files, databases, vector stores, caches, YAML files, or ad hoc memory blobs for MVP.
- Fail closed when the destination file, record type, source context, approval state, or storage path is unclear.
