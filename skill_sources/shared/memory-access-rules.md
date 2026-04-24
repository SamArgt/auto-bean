# Memory Access Rules

Durable auto-bean memory lives under `.auto-bean/memory/` in the user workspace. It is local, versionable, inspectable, and separate from `ledger.beancount`, `beancount/**`, `statements/raw/`, and `statements/parsed/`.

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

Memory may guide future workflows, but it never replaces current evidence checks, ledger validation, finding review, user clarification, or commit/push approval.
