# Memory Access Rules

Durable auto-bean memory lives under `.auto-bean/memory/` in the user workspace. It is local, versionable, inspectable, and separate from `ledger.beancount`, `beancount/**`, `statements/raw/`, and `statements/parsed/`.

## Durable memory writes

Only the governed memory workflow may modify `.auto-bean/memory/**`. Other skills may identify eligible reusable decisions and request persistence, but they must not own direct memory writes.

Eligible memory categories:

- `account_mapping`
- `category_mapping`
- `naming_convention`
- `import_source_behavior`
- `transfer_detection`
- `deduplication_decision`
- `clarification_outcome`

Every durable record must include `schema_version`, `memory_type`, `source`, `decision`, `scope`, `confidence` or `review_state`, `created_at`, `updated_at`, and `audit`.

Use these fixed files for MVP memory:

- `.auto-bean/memory/account_mappings.json`
- `.auto-bean/memory/category_mappings.json`
- `.auto-bean/memory/naming_conventions.json`
- `.auto-bean/memory/transfer_detection.json`
- `.auto-bean/memory/deduplication_decisions.json`
- `.auto-bean/memory/clarification_outcomes.json`
- `.auto-bean/memory/import_sources/index.json`
- `.auto-bean/memory/import_sources/<source_slug>.json`

Read `.auto-bean/memory/import_sources/index.json` before reading or writing import-source behavior. The index points to the one memory file for each known statement source.

Persist only approved reusable decisions. Do not persist tentative guesses, blocked findings, rejected interpretations, validation-failed outcomes, or unresolved clarifications unless the user explicitly approves storing that learning.

## Advisory memory reads

Non-memory workflows may read the fixed governed JSON files above as advisory context only. For import-source behavior, read `.auto-bean/memory/import_sources/index.json` first and read a source file only when the index entry matches current source identity, institution, account hints, statement shape, or source fingerprint.

Always fail closed when memory is missing, malformed, stale, too broad, inconsistent with current evidence, has the wrong schema or type, lacks required record fields, or would skip ledger validation, user clarification, finding review, or commit/push approval. A memory record may influence a proposal only after it is checked against current parsed statement facts, current ledger state, account constraints, and reconciliation evidence relevant to the decision.

Every memory-influenced decision must carry review attribution: memory path, `memory_type`, record identity or stable summary, matched current evidence, decision influenced, and limits on reuse such as confidence, scope, conflicts checked, or why the memory stayed advisory. Memory may guide future workflows, but it never replaces current evidence checks, ledger validation, finding review, user clarification, or commit/push approval.
