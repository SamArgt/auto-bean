# Memory Access Rules

Purpose: canonical rules for reading and writing governed `.auto-bean/memory/**` records.

Durable auto-bean memory lives under `.auto-bean/memory/` in the user workspace. It is local, versionable, inspectable, and separate from `ledger.beancount`, `beancount/**`, `statements/raw/`, and `statements/parsed/`.

Memory is advisory: check it against current evidence before reuse, and never let it replace validation, clarification, review, or approval.

`.auto-bean/memory/MEMORY.md` is always-loaded workspace memory. Read it at the start of every new Codex session and include it in every sub-agent handoff. It gathers user profile information such as main accounts, important account relationships, institutions or statement sources, user preferences, user corrections, and other reusable context that is not owned by a workflow-specific memory file.

## Fixed files

Use these fixed files for MVP memory:

- `.auto-bean/memory/MEMORY.md`
- `.auto-bean/memory/account_mappings.json`
- `.auto-bean/memory/category_mappings.json`
- `.auto-bean/memory/transfer_detection.json`
- `.auto-bean/memory/deduplication_decisions.json`
- `.auto-bean/memory/commodity_price_sources.json`
- `.auto-bean/memory/import_sources/index.json`
- `.auto-bean/memory/import_sources/<source_slug>.json`

Eligible memory categories:

- `account_mapping`
- `category_mapping`
- `import_source_behavior`
- `transfer_detection`
- `deduplication_decision`
- `commodity_price_source`
- `global_memory`

Every durable workflow-specific JSON record must include `schema_version`, `memory_type`, `source`, `decision`, `scope`, `confidence` or `review_state`, `created_at`, `updated_at`, and `audit`.

Workflow-specific JSON files must use the top-level shape `schema_version`, `memory_type`, and `records`. Import-source behavior must read `.auto-bean/memory/import_sources/index.json` first; source files are valid only when referenced by an index entry whose path stays under `.auto-bean/memory/import_sources/`.

Use workflow-specific files only at their relevant workflow stages:

- `.auto-bean/memory/import_sources/index.json` and matching import-source files: discovery and raw-to-parsed processing.
- `.auto-bean/memory/account_mappings.json`: account inspection, statement account matching, and transaction posting handoffs.
- `.auto-bean/memory/category_mappings.json`: categorization and posting handoffs.
- `.auto-bean/memory/transfer_detection.json`: reconciliation, transfer detection, and posting-risk review.
- `.auto-bean/memory/deduplication_decisions.json`: deduplication and posting-risk review.
- `.auto-bean/memory/commodity_price_sources.json`: commodity price lookup source selection and price-update workflows.
- `.auto-bean/memory/MEMORY.md`: every new session and every sub-agent handoff, plus main-thread end-of-session review and memory inspection/correction/persistence work.

## Reading memory

Read `.auto-bean/memory/MEMORY.md` directly and summarize only relevant sections in conversation or handoff messages. Do not dump the whole file unless the user asks to inspect it. If you are running as a sub-agent, do not write this file; include suggested additions, replacements, or removals in your return instead.

SHOULD prefer `jq` for memory inspection, especially when files are large. Query only the fields needed for the task instead of dumping entire files into the conversation.

List record counts:

```sh
jq '{memory_type, count: (.records // [] | length)}' .auto-bean/memory/category_mappings.json
```

Show compact summaries:

```sh
jq -r '.records[] | [.memory_type, (.source.summary // .source.description // "unknown source"), (.decision.summary // .decision.pattern // "no summary"), (.scope.description // "no scope"), (.confidence // .review_state // "unreviewed")] | @tsv' .auto-bean/memory/account_mappings.json
```

Find records matching a merchant, account, or other text:

```sh
jq '.records[] | select((. | tostring | ascii_downcase) | contains("merchant name"))' .auto-bean/memory/category_mappings.json
```

Inspect import-source index entries before opening source files:

```sh
jq -r '.sources[] | [.source_slug, .path, (.institution // ""), (.account_owner // ""), ((.account_names // []) | join(", ")), (.account_hint // "")] | @tsv' .auto-bean/memory/import_sources/index.json
```

Read only the indexed import-source file that matches the current source:

```sh
jq '.records[] | {memory_type, source, decision, scope, confidence, review_state, updated_at}' .auto-bean/memory/import_sources/<source_slug>.json
```

When memory is missing, malformed, stale, too broad, inconsistent with current evidence, path-unsafe, or schema-incompatible, skip or flag it and continue where possible.

When memory influences a proposal, include review attribution: memory path, `memory_type`, record identity or stable summary, matched current evidence, decision influenced, and limits on reuse such as confidence, scope, conflicts checked, or why the memory stayed advisory.


Guardrails:

- Only `$auto-bean-memory` may modify workflow-specific JSON memory files: `.auto-bean/memory/*.json` and `.auto-bean/memory/import_sources/*.json`.
- Main-thread orchestrators and direct main-thread write sessions may update `.auto-bean/memory/MEMORY.md` for durable global user profile, preference, correction, and general workspace context.
