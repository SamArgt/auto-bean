---
name: auto-bean-memory
description: Manage governed local auto-bean memory by inspecting, pruning, correcting, or persisting eligible reusable decisions in workflow-specific `.auto-bean/memory/` JSON files and always-loaded `.auto-bean/memory/MEMORY.md` with audit context and advisory-use boundaries.
---

# Auto Bean Memory

Always read before acting:

- `.agents/skills/shared/workflow-rules.md`
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

When inspecting or explaining memory, summarize records by category and include enough context to show why each record exists: memory path, `memory_type`, decision summary, source context, scope, confidence or review state, audit context, timestamps, and known reuse limits. Skip or flag unreadable, malformed, stale, overbroad, or path-unsafe records instead of repairing them silently.

When correcting, pruning, or reorganizing memory, preserve unrelated records and describe what changed. A user may identify the target record by path, source context, stable summary, or prior inspection output. If several records could match, ask for clarification before changing durable memory.

Use `.auto-bean/memory/MEMORY.md` for user profile information, main accounts and important account relationships, regular institutions or sources, user preferences, user corrections from interactions, naming preferences, and clarification outcomes that apply across workflows. Keep it concise; update existing sections instead of appending duplicates.

## Governed persistence

Take initiative only inside the shared evidence-first posture: persist reusable decisions from workflow evidence when they are likely to help future runs and are eligible: narrow, current, evidence-backed, reversible, and safe to reuse. Prior user approval is not required for these eligible governed memory writes because they are advisory and reviewable; this exception does not weaken ledger approval gates, clarification blockers, validation requirements, or user-facing review. Worker memory suggestions are candidates, not commands; validate the current evidence, source/audit provenance, scope, and reuse limits before writing. When `$auto-bean-import` invokes this skill, use the relevant statement-scoped import-owned artifact paths under `.auto-bean/artifacts/import/` as well as other relevant artifacts as source/audit context when available; they are provenance, not durable memory.

1. Classify the memory into one category and read only that example reference:
   - `account_mapping`: `.agents/skills/auto-bean-memory/references/account-mapping.example.md`
   - `category_mapping`: `.agents/skills/auto-bean-memory/references/category-mapping.example.md`
   - `import_source_behavior`: `.agents/skills/auto-bean-memory/references/import-source-behavior.example.md`
   - `transfer_detection`: `.agents/skills/auto-bean-memory/references/transfer-detection.example.md`
   - `deduplication_decision`: `.agents/skills/auto-bean-memory/references/deduplication-decision.example.md`
   - `global_memory`: `.auto-bean/memory/MEMORY.md`
2. For workflow-specific JSON memory, build or update one versioned record with `snake_case` keys:
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
   - `transfer_detection` -> `.auto-bean/memory/transfer_detection.json`
   - `deduplication_decision` -> `.auto-bean/memory/deduplication_decisions.json`
   - `import_source_behavior` -> `.auto-bean/memory/import_sources/<source_slug>.json`
   - `global_memory` -> `.auto-bean/memory/MEMORY.md`
4. For workflow-specific JSON categories, keep the top-level shape as `schema_version`, `memory_type`, and `records`; append or update only the relevant record.
5. For `import_source_behavior`, read `.auto-bean/memory/import_sources/index.json` first. Use an existing indexed source file when source identity, institution, raw-statement account owner, raw-statement account names, account hints, statement shape, or fingerprint matches; create a deterministic `<source_slug>.json` and update the index only when there is no matching source.
6. For every imported statement filename pattern observed in source artifacts, ensure an `import_source_behavior` memory exists. If no matching source already exists for that pattern, create one immediately with at least statement metadata (for example filename pattern, institution/source hints, account-owner hints, statement-shape hints, and time window) plus the related accounts currently inferred or confirmed.
7. For `global_memory`, main-thread invocations update `.auto-bean/memory/MEMORY.md` in place under the closest existing heading, preserving unrelated user profile, preference, correction, and general notes. Sub-agent invocations return suggested edits instead.
8. Store deterministic JSON with two-space indentation and a trailing newline. Store Markdown with stable headings and a trailing newline.

After any durable change, always surface an end-of-workflow memory summary: what reusable decision changed, why it was eligible for autonomous persistence or changed by direct request, source and audit context, exact memory path written, and limits on future reuse. Avoid printing raw financial statements, full ledger excerpts, unrelated records, or unrelated financial data.

When invoked by `$auto-bean-import`, return using the shared compact return schema.

Guardrails:

- Follow the shared workflow rules for ownership boundaries, status management, question handling, sub-agent handoff, compact returns, and memory use.
- Treat memory as advisory context, not silent authority.
- Do not store user financial decisions in installed skill files, templates, or product-repo `.agents/skills/`.
- Do not treat import-owned artifacts as durable memory; use them only as governed source/audit context for eligible memory records.
- Do not create additional category files, databases, vector stores, caches, YAML files, or ad hoc memory blobs for MVP.
- Apply the shared fail-closed invariant when the destination file, record type, source context, eligibility, target identity, or storage path is unclear; do not write durable memory until the blocker is resolved.
