---
name: auto-bean-prices
description: Fetch and review Beancount commodity prices. Use for current price updates, explicit historical backfills, or an import price epilogue.
---

Read [common guidance](../../references/common.md) once for runtime, ownership, advisory memory and validation. This skill owns proposed `price` directives; `$auto-bean:auto-bean-memory` owns durable commodity-source hints.

For an import invocation, read [import data](../../references/import-review.md#state-and-validation) and [ownership](../../references/common.md#ownership). For a direct request, use Write's [direct-review procedure](../auto-bean-write/SKILL.md#direct-review).

## Workflow

1. Establish whether this is a normal price update, an import epilogue, or an explicitly requested historical backfill. Inspect the root ledger and relevant includes for active commodities, operating currency, commodity metadata, current prices and price-file placement. Use `$auto-bean:auto-bean-query` when held-commodity analysis is needed.
2. Select sources using explicit ledger metadata, then narrowly matching advisory `commodity_price_sources.json`. Read [source selection](references/price-reference.md#source-selection) when a mapping must be found or verified, and [commodity semantics](../../references/ledger-reference.md#commodities) when directives need checking. Missing coverage or ambiguous identity remains a blocker.
3. Follow [fetch and completion](references/price-reference.md#fetch-and-completion) for every run or source probe: one dated snapshot by default, matching preflight, bounded execution, terminal outcome and reconciliation of every job. Create the [run record](references/price-reference.md#run-record) before fetching and update it on resume, using the [session schema](../../references/schemas/session.schema.json) for import JSON.
4. Prepare supported directives targeting the existing price file, otherwise the included `beancount/prices.beancount`. If no price include exists, propose its minimal addition. Preserve actual provider quote dates; disclose stale or mismatched dates. Deduplicate only equal date/commodity/quote-currency/value tuples; conflicting values need review. Keep unrelated price history unchanged.
5. For imports, keep proposed directives in the run jobs, obtain separate approval for new directives, then write them directly to the ledger. No new directives means no write approval round. For direct requests, follow direct review. Run [shared validation](../../references/common.md#validation), with `--session <id> --stage written` for imports and without a session for direct work. Use the price-run report and shared ledger checks to assess this work; unrelated pending statements do not make a successful price result fail. Affected failures remain unresolved. Do not add unrelated declarations, plugin options or include changes.
6. Present the run record, terminal outcome, changed files, prices, skipped coverage, source confidence, validation and unresolved source identity. Earlier statement approval never covers later price writes. For imports, return accepted price-source evidence to Import for its memory handoff. For standalone work, `$auto-bean:auto-bean-memory` can derive eligible source hints after acceptance and verification; no separate suggestion record is needed.

Serialize writes with other ledger writers and check that approved run directives still match before writing. Recheck current ledger prices to avoid duplicate appends. Import receives the compact handoff with blockers, pending inputs, changed files and validation. Pending price approval or a failed price stage stays in session state without reversing completed statements. Never describe a still-running or partially accounted fetch as completed.
