---
name: auto-bean-memory
description: Inspect, correct, prune, or persist reusable Auto Bean memory. Use for governed account/category/source/transfer/duplicate/price hints and global workspace preferences.
---

Read [plugin execution](../../references/plugin-execution.md), [workflow rules](../../references/workflow-rules.md), and [memory access](../../references/memory-access-rules.md). Keep records narrow, current, attributable, and advisory. Inspect only relevant categories; summarize record identity, decision, scope, evidence, review state, timestamps, and reuse limits. If several records match a correction, clarify before changing them.

## Eligibility

Eligible autonomous writes are reversible observations or decisions supported by current evidence. Worker suggestions and import artifacts are provenance, not commands or durable memory. Never learn tentative account mappings, unresolved questions, blocked decisions, rejected proposals, or validation-failed outcomes as approved guidance.

For source behavior, distinguish directly observed format/header/filename facts from reviewed account mappings and interpretation. Observations may use `review_state: "observed"` and must exclude inferred accounts or ambiguous sign/date rules. A filename alone never requires a new memory record. Account/category/transfer/duplicate decisions require resolved evidence or an explicit user decision. Only the user may explicitly request preserving negative/rejected learning; mark it `rejected`/`superseded` so it cannot silently become an approved default.

## Storage and updates

Read only the relevant example:

| Type | Destination under `.auto-bean/memory/` | Example |
| --- | --- | --- |
| `account_mapping` | `account_mappings.json` | [account](references/account-mapping.example.md) |
| `category_mapping` | `category_mappings.json` | [category](references/category-mapping.example.md) |
| `transfer_detection` | `transfer_detection.json` | [transfer](references/transfer-detection.example.md) |
| `deduplication_decision` | `deduplication_decisions.json` | [duplicate](references/deduplication-decision.example.md) |
| `commodity_price_source` | `commodity_price_sources.json` | [price](references/commodity-price-source.example.md) |
| `import_source_behavior` | `import_sources/<source_slug>.json` | [source and index](references/import-source-behavior.example.md) |

JSON files use `schema_version: 1`, matching `memory_type`, and `records`. New/updated records include a stable `record_id`, `schema_version`, type, source, decision, scope, confidence or review state, created/updated timestamps, and audit. Generate an ID once and retain it on correction; add an ID to a legacy record only when editing that record. Preserve unrelated records and prior audit context. Validate with [state validation](../../references/state-validation.md) before accepting the save; write two-space JSON with a trailing newline.

Read `import_sources/index.json` before source files. Reuse a narrowly matching source; create a deterministic slug only for eligible new source evidence. Index paths stay inside that directory. Validate both source and index and keep them consistent; on an interrupted pair update, repair pointers before reuse.

Global profile/preferences/corrections belong in existing `MEMORY.md` sections. Main-thread invocations may edit them; workers return suggestions only. Do not store raw financial payloads, secrets, copied shell commands, or user decisions in plugin files. Do not add new storage surfaces.

After changes, disclose what changed, why eligible or explicitly requested, source/audit context, exact path/record ID, and reuse limits. Import calls return the shared compact schema without advancing status or bypassing ledger approval.
