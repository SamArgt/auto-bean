# Memory Access Rules

Purpose: canonical rules for reading and writing governed `.auto-bean/memory/**` records.

Durable auto-bean memory lives under `.auto-bean/memory/` in the user workspace. It is local, versionable, inspectable, and separate from `ledger.beancount`, `beancount/**`, `statements/raw/`, and `statements/parsed/`.

Memory is advisory: check it against current evidence before reuse, and never let it replace validation, clarification, review, or approval.

## Fixed files

Use these fixed files for MVP memory:

- `.auto-bean/memory/account_mappings.json`
- `.auto-bean/memory/category_mappings.json`
- `.auto-bean/memory/naming_conventions.json`
- `.auto-bean/memory/transfer_detection.json`
- `.auto-bean/memory/deduplication_decisions.json`
- `.auto-bean/memory/clarification_outcomes.json`
- `.auto-bean/memory/import_sources/index.json`
- `.auto-bean/memory/import_sources/<source_slug>.json`

Eligible memory categories:

- `account_mapping`
- `category_mapping`
- `naming_convention`
- `import_source_behavior`
- `transfer_detection`
- `deduplication_decision`
- `clarification_outcome`

Every durable record must include `schema_version`, `memory_type`, `source`, `decision`, `scope`, `confidence` or `review_state`, `created_at`, `updated_at`, and `audit`.

Non-import-source files must use the top-level shape `schema_version`, `memory_type`, and `records`. Import-source behavior must read `.auto-bean/memory/import_sources/index.json` first; source files are valid only when referenced by an index entry whose path stays under `.auto-bean/memory/import_sources/`.

## Reading memory

Prefer `jq` for memory inspection, especially when files are large. Query only the fields needed for the task instead of dumping entire files into the conversation.

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

## Writing memory

Only `$auto-bean-memory` may modify `.auto-bean/memory/**`. Other skills may identify eligible reusable decisions and request persistence, but they must not own direct memory writes.

Persist only approved reusable decisions. Do not persist tentative guesses, blocked findings, rejected interpretations, validation-failed outcomes, or unresolved clarifications unless the user explicitly approves storing that learning.

Before writing, validate with `jq` or another structured JSON parser:

```sh
jq empty .auto-bean/memory/category_mappings.json
jq '.schema_version == 1 and .memory_type == "category_mapping" and (.records | type == "array")' .auto-bean/memory/category_mappings.json
```

For import-source behavior, validate the index before reading or editing any source file, and edit only valid index entries under `.auto-bean/memory/import_sources/`.

Preserve unrelated records, keep deterministic two-space JSON with a trailing newline, and avoid broad rewrites or new storage systems. Fail closed when the destination file, record type, source context, approval state, target identity, or storage path is unclear.
