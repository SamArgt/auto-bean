---
name: auto-bean-prices
description: Update Beancount commodity price directives from external sources using bean-price first and web search when a beanprice source needs to be discovered. Use after imports or direct price-update requests when Codex needs to fetch current prices for held ledger commodities, maintain `.auto-bean/memory/commodity_price_sources.json` source mappings, draft price directives, validate the ledger, and surface reviewable price-update results.
---

Use this for commodity price updates. It owns drafted `price` directives, while `$auto-bean-memory` owns durable commodity-source memory.

MUST read before acting:

- `.auto-bean/memory/MEMORY.md`
- `.agents/skills/shared/workflow-rules.md`
- `.agents/skills/shared/memory-access-rules.md`
- `.agents/skills/shared/beancount-syntax-and-best-practices.md`
- `.agents/skills/auto-bean-prices/references/price-source-selection.md`

## Workflow

1. Restate whether this is a direct price update or an import-invoked epilogue.
2. Inspect the ledger before fetching prices:
   - read `ledger.beancount` and relevant included `beancount/**` files
   - find existing `commodity` directives, `price` directives, commodity metadata, price file placement, and operating currency
   - use `bean-query` through `$auto-bean-query` or direct `bean-query` only to identify active held commodities when needed
3. Read `.auto-bean/memory/commodity_price_sources.json` if it exists.
   - If it is missing, malformed, path-unsafe, or schema-incompatible, apply the shared fail-closed memory rules and continue only with explicit ledger metadata or user-approved evidence.
   - Treat price-source memory as advisory; verify it against current commodity names, quote currency, and ledger conventions.
4. Select the narrowest source for each active commodity:
   - prefer commodity metadata such as `price: "USD:yahoo/AAPL"` when present
   - otherwise use a matching `commodity_price_source` memory record
   - otherwise search for a working beanprice source string using the source-selection reference
   - if beanprice coverage is not available, use web search to find an authoritative current price page and record the proposed source for review
   - if the source is still ambiguous, record a blocker instead of guessing
5. Fetch prices:
   - prefer `./.venv/bin/bean-price --update ledger.beancount` when commodity metadata is complete
   - probe exact source expressions with `./.venv/bin/bean-price -e '<QUOTE>:<SOURCE>/<SYMBOL>'` when metadata or memory provides a candidate source
   - use web search only to discover or verify source mappings and authoritative price pages when beanprice cannot provide the commodity
6. Draft price directives in the narrowest existing price target:
   - prefer the ledger's existing price file
   - otherwise use `beancount/prices.beancount` when it is included
   - if no price include exists, propose the minimal include plus `beancount/prices.beancount` before writing prices
   - deduplicate exact date, commodity, and quote-currency repeats; never rewrite unrelated historical prices
7. Validate after drafting:
   - prefer `./scripts/validate-ledger.sh`
   - otherwise use `./.venv/bin/bean-check ledger.beancount`
   - if validation fails, leave the draft in place, report the failure, and do not claim completion
8. Present a concise review package:
   - changed files
   - prices added, skipped commodities, and source confidence
   - validation result
   - any `commodity_price_source` memory suggestions for `$auto-bean-memory`
   - a clear statement that price directives are ledger changes requiring review before final acceptance

When invoked by `$auto-bean-import`, return using the shared compact return schema with `blockers`, `pending_questions`, `memory_suggestions`, `mutation.changed_files`, and `validation`.

When this is a direct price update request, wait for user review and approval before finalizing the price updates. After approval, persist any reviewed `$auto-bean-memory` suggestions for commodity sources.

## Guardrails

- Do not store API keys, tokens, account identifiers, or shell snippets in memory or artifacts.
- Do not guess source mappings for ambiguous tickers, similarly named funds, local listings, or private assets.
- Do not overwrite or normalize unrelated existing price history.
- Do not silently add commodity declarations, plugin options, or include-graph changes beyond the minimal approved price file/include.
- Do not use web search snippets as authoritative prices without recording the source URL, timestamp, quote currency, and uncertainty.
