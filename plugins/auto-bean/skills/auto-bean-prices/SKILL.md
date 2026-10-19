---
name: auto-bean-prices
description: Fetch and review Beancount commodity prices. Use for current price updates, explicit historical backfills, or an import price epilogue.
---

Read [plugin execution](../../references/plugin-execution.md) before acting. Resolve resource paths relative to the file containing them; resolve financial-data paths against the selected workspace.


Use this for commodity price updates. It owns drafted `price` directives, while `$auto-bean:auto-bean-memory` owns durable commodity-source memory.

MUST read before acting:

- `.auto-bean/memory/MEMORY.md`
- `../../references/workflow-rules.md`
- `../../references/candidate-review.md`
- `references/price-run-contract.md`

## Workflow

1. Restate whether this is a direct price update or an import-invoked epilogue.
2. Inspect the ledger before fetching prices:
   - read `ledger.beancount` and relevant included `beancount/**` files
   - find existing `commodity` directives, `price` directives, commodity metadata, price file placement, and operating currency
   - use `bean-query` through `$auto-bean:auto-bean-query` or direct `bean-query` only to identify active held commodities when needed
3. Read [memory rules](../../references/memory-access-rules.md) and `.auto-bean/memory/commodity_price_sources.json` when selecting advisory mappings. Read [source selection](references/price-source-selection.md) only when discovering a source.
   - If it is missing, malformed, path-unsafe, or schema-incompatible, apply the shared fail-closed memory rules and continue only with explicit ledger metadata or user-approved evidence.
   - Treat price-source memory as advisory; verify it against current commodity names, quote currency, and ledger conventions.
4. Read [ledger semantics](../../references/beancount-syntax-and-best-practices.md) only when directive syntax needs checking. Select the narrowest source for each active commodity:
   - prefer commodity metadata such as `price: "USD:yahoo/AAPL"` when present
   - otherwise use a matching `commodity_price_source` memory record
   - otherwise search for a working beanprice source string using the source-selection reference
   - if beanprice coverage is not available, use web search to find an authoritative current price page and record the proposed source for review
   - if the source is still ambiguous, record a blocker instead of guessing
5. Choose and execute one fetch mode using the price-run contract:
   - for an import epilogue or normal price update, fetch one explicit snapshot with `auto_bean bean-price --date <target-date> ledger.beancount`; do not add `--update`
   - preflight every fetch, including snapshots and probes, with the same arguments plus `--dry-run`; record the job count before executing live with verbose logging as specified in the price-run contract
   - use `--update` only for an explicitly requested historical backfill
   - if the command yields a running session, keep polling that same session until it returns a terminal exit code; an empty or partial output chunk is never completion
   - reconcile the completed live run against its dry-run job count before drafting directives or claiming success
   - probe exact source expressions with `auto_bean bean-price -e '<QUOTE>:<SOURCE>/<SYMBOL>'` when metadata or memory provides a candidate source
   - use web search only to discover or verify source mappings and authoritative price pages when beanprice cannot provide the commodity
6. Draft price directives in the narrowest existing price target:
   - prefer the ledger's existing price file
   - otherwise use `beancount/prices.beancount` when it is included
   - if no price include exists, propose the minimal include plus `beancount/prices.beancount` before writing prices
   - retain the provider's actual quote date; do not relabel a stale/weekend quote as the requested date. Disclose and review any date mismatch or stale quote before writing
   - deduplicate date, commodity, and quote-currency repeats only when values also agree; conflicting values require review; never rewrite unrelated historical prices
7. Validate after drafting:
   - use `auto_bean bean-check ledger.beancount`
   - if validation fails, leave the draft in place, report the failure, and do not claim completion
8. Present a concise review package:
   - price artifact path and terminal fetch status
   - changed files
   - prices added, skipped commodities, and source confidence
   - validation result
   - any `commodity_price_source` memory suggestions for `$auto-bean:auto-bean-memory`
   - a clear statement that price directives are ledger changes requiring review before final acceptance

Serialize the mutation with all other ledger writers and bind review to candidate hashes. When invoked by `$auto-bean:auto-bean-import`, return using the shared compact return schema with `blockers`, `pending_questions`, `memory_suggestions`, `mutation.changed_files`, and `validation`.

For direct requests, the session owns final price approval. For import epilogues, import obtains separate explicit approval of the price candidate; earlier statement approval never covers later price edits. Keep pending price approval in the price artifact without reversing completed statement status. After approval, persist any reviewed `$auto-bean:auto-bean-memory` suggestions for commodity sources.

## Guardrails

- Do not store API keys, tokens, account identifiers, or shell snippets in memory or artifacts.
- Do not guess source mappings for ambiguous tickers, similarly named funds, local listings, or private assets.
- Do not overwrite or normalize unrelated existing price history.
- Do not replace an unresolved bulk run with narrower probes while claiming that the bulk operation completed.
- Do not silently add commodity declarations, plugin options, or include-graph changes beyond the minimal approved price file/include.
- Do not use web search snippets as authoritative prices without recording the source URL, timestamp, quote currency, and uncertainty.
