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
5. For imports, keep proposed directives in the run jobs, obtain separate approval for new directives, then write them directly to the ledger. No new directives means no write approval round. For direct requests, follow direct review. Run [shared validation](../../references/common.md#validation), with `--session <id> --price-run <run-id> --stage written` for each import price run, including no-op runs, and without a session for direct work. This checks the selected price result and shared ledger without replacing pending statement reports. Affected failures remain unresolved. Do not add unrelated declarations, plugin options or include changes.
6. Present the run record, outcome, changed files, prices, skipped coverage, validation and unresolved identity. Earlier statement approval never covers later price writes. Return source evidence to Import, or invoke `$auto-bean:auto-bean-memory` for standalone learning. Memory owns eligibility, including verified redundant results; no separate suggestion record is needed.

Before writing, recheck approved directives and current prices to avoid duplicate appends. Follow common serialization and session-validation coordination. Return blockers, pending inputs, changed files and validation to Import. Pending approval or failures remain in session state without reversing completed statements. Never call a running or partly accounted fetch complete.
