---
name: auto-bean-memory
description: Manage governed local auto-bean memory by inspecting, pruning, correcting, or persisting approved reusable decisions in fixed `.auto-bean/memory/` JSON files with audit context and advisory-use boundaries.
---

# Auto Bean Memory

Read this reference before acting:

- `.agents/skills/shared/memory-access-rules.md`

Use this skill when the user asks to inspect, review, explain, correct, prune, reorganize, or persist reusable auto-bean memory.

## Managing memory

Memory is durable advisory context for future workflows. Keep it small, reviewable, and tied to evidence. Use judgment to decide whether the task is an inspection, cleanup, correction, or persistence request, and keep the response focused on the user's goal.

Good memory records are:

- reusable across future imports, categorization, writing, or review work
- narrow enough to be checked against current evidence
- backed by source and audit context
- stored in the fixed memory files described by the shared access rules

Avoid storing:

- raw statements, parsed statement payloads, full ledger excerpts, diagnostics, or proposal artifacts
- tentative guesses, unresolved clarifications, rejected interpretations, blocked findings, or validation-failed outcomes unless the user explicitly wants to preserve that learning
- broad preferences that would bypass current evidence, ledger validation, user clarification, finding review, or commit/push approval

When inspecting or explaining memory, summarize records by category and include enough context to show why each record exists: memory path, `memory_type`, decision summary, source context, scope, confidence or review state, audit context, timestamps, and known reuse limits. Skip or flag unreadable, malformed, stale, overbroad, or path-unsafe records instead of repairing them silently.

When correcting, pruning, or reorganizing memory, preserve unrelated records and describe what changed. A user may identify the target record by path, source context, stable summary, or prior inspection output. If several records could match, ask for clarification before changing durable memory.

## Governed persistence

Persist only reusable decisions from an approved or finalized workflow result, or from a direct user request to remember a reusable rule. When `$auto-bean-import` invokes this skill, use the relevant statement-scoped import-owned artifact paths under `.auto-bean/artifacts/import/` as source/audit context when available; they are provenance, not durable memory.

1. Classify the memory into one category and read only that example reference:
   - `account_mapping`: `.agents/skills/auto-bean-memory/references/account-mapping.example.md`
   - `category_mapping`: `.agents/skills/auto-bean-memory/references/category-mapping.example.md`
   - `naming_convention`: `.agents/skills/auto-bean-memory/references/naming-convention.example.md`
   - `import_source_behavior`: `.agents/skills/auto-bean-memory/references/import-source-behavior.example.md`
   - `transfer_detection`: `.agents/skills/auto-bean-memory/references/transfer-detection.example.md`
   - `deduplication_decision`: `.agents/skills/auto-bean-memory/references/deduplication-decision.example.md`
   - `clarification_outcome`: `.agents/skills/auto-bean-memory/references/clarification-outcome.example.md`
2. Build or update one versioned record with `snake_case` keys:
   - `schema_version`
   - `memory_type`
   - `source`
   - `decision`
   - `scope`
   - `confidence` or `review_state`
   - `created_at`
   - `updated_at`
   - `audit`
3. Choose the destination from the fixed map:
   - `account_mapping` -> `.auto-bean/memory/account_mappings.json`
   - `category_mapping` -> `.auto-bean/memory/category_mappings.json`
   - `naming_convention` -> `.auto-bean/memory/naming_conventions.json`
   - `transfer_detection` -> `.auto-bean/memory/transfer_detection.json`
   - `deduplication_decision` -> `.auto-bean/memory/deduplication_decisions.json`
   - `clarification_outcome` -> `.auto-bean/memory/clarification_outcomes.json`
   - `import_source_behavior` -> `.auto-bean/memory/import_sources/<source_slug>.json`
4. For non-import-source categories, keep the top-level shape as `schema_version`, `memory_type`, and `records`; append or update only the relevant record.
5. For `import_source_behavior`, read `.auto-bean/memory/import_sources/index.json` first. Use an existing indexed source file when source identity, institution, account hints, statement shape, or fingerprint matches; create a deterministic `<source_slug>.json` and update the index only when there is no matching source.
6. Store deterministic JSON with two-space indentation and a trailing newline.

After any durable change, give a concise review summary: what reusable decision changed, why it is eligible, source and audit context, exact memory path written, and limits on future reuse. Avoid printing raw financial statements, full ledger excerpts, unrelated records, or unrelated financial data.

Guardrails:

- Treat memory as advisory context, not silent authority.
- Do not store user financial decisions in installed skill files, templates, or product-repo `.agents/skills/`.
- Do not write `.auto-bean/memory/**` from import, categorize, query, process, or write workflows directly; those workflows may identify reusable learning and hand it to this skill.
- Do not treat import-owned artifacts as durable memory; use them only as governed source/audit context for eligible memory records.
- Do not create additional category files, databases, vector stores, caches, YAML files, or ad hoc memory blobs for MVP.
- Fail closed when the destination file, record type, source context, approval state, target identity, or storage path is unclear.
