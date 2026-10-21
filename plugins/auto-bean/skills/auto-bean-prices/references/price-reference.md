# Price sources and execution

## Source selection

Prefer explicit commodity metadata such as `price: "USD:yahoo/AAPL"`, then a matching governed source hint checked against current commodity identity and quote currency. For an unknown mapping, use the commodity name, exchange, ISIN/CUSIP, provider and share class to find an exact supported source. Do not infer identity from a ticker alone.

Check current Beanprice documentation through Context7 or its official source for supported providers and expression syntax. Common starting points include Yahoo for listed securities, ECB for compatible EUR-based FX and Coinbase for supported crypto; availability and historical coverage must be verified. Use the [fetch protocol](#fetch-and-completion) for each source probe and retain the exact successful expression as evidence.

When Beanprice coverage is unavailable, prefer an issuer, exchange, central bank or fund-provider page. Record its URL, retrieval timestamp, quote currency and uncertainty; search snippets alone are not authoritative prices. Review source conflicts and ambiguous local listings, share classes or private assets before reuse. When the Memory skill persists an eligible source rule, its decision uses one of these shapes:

```json
{"method_type": "beanprice", "commodity": "AAPL", "quote_currency": "USD", "source": "USD:yahoo/AAPL"}
```

```json
{"method_type": "web_search", "commodity": "EXAMPLE", "quote_currency": "EUR", "source_url": "https://www.example.com/markets/example", "query": "EXAMPLE fund NAV EUR official"}
```

## Fetch and completion

For normal updates and import epilogues, use one explicit dated `snapshot` without `--update`. Preflight lists jobs; the live command retains the same date, sources and selection flags and adds verbose logging:

```sh
auto_bean bean-price --dry-run --date <target-date> ledger.beancount
auto_bean bean-price -v --date <target-date> ledger.beancount
```

Apply the same contract to exact-source probes:

```sh
auto_bean bean-price --dry-run --date <target-date> -e '<QUOTE>:<SOURCE>/<SYMBOL>'
auto_bean bean-price -v --date <target-date> -e '<QUOTE>:<SOURCE>/<SYMBOL>'
```

Use `historical_backfill` only when the user explicitly requests historical coverage. Dry-run the exact `--update` command first, recording its target range and job count. Every live fetch requires a successful preflight; stop when it fails. Count listed jobs, not stderr lines. Use Beanprice's default workers unless the user explicitly requests a concurrency change.

Allow 180 seconds per fetch, excluding runtime preparation. On timeout, terminate that same process/session and collect its terminal result; do not start competing retries. Retry a clearly transient failure at most once, after the original terminates. Poll a running session until its terminal exit code arrives: an empty chunk or partial stdout is not completion. Verbose logs must account for redundant directives and provider failures. Do not substitute narrower probes or fallback directives while the original run is unresolved.

Reconcile every dry-run job before drafting directives or claiming success. Zero emitted directives alone proves neither success nor failure. Classify outcomes as follows:

| Context | Outcome | Required evidence |
| --- | --- | --- |
| Standalone | `succeeded` | Exit zero, no provider errors, every job emitted or explicitly logged as redundant. |
| Standalone | `no_op` | Exit zero and either no jobs or every job explicitly logged as redundant. |
| Standalone | `failed` | Nonzero exit, provider error or unaccounted job. |
| Import JSON | `complete` | Successful terminal execution with every required commodity and preflight job accounted for; all-redundant runs qualify. |
| Import JSON | `no_op` | No commodities require fetching and there are zero jobs. |
| Import JSON | `partial` | Mixed accounted successes and unresolved jobs or coverage. |
| Import JSON | `failed` | Failed execution. |

Do not put standalone `succeeded` in import JSON. Preserve actual execution state, exit code, duration, source coverage and each job's emitted/redundant/skipped/failed/unaccounted outcome. Required commodities are separate from jobs: zero jobs cannot conceal missing source coverage.

## Run record

Before fetching, create/update `session.price_runs` for an import, or `.auto-bean/artifacts/prices/<run-id>--prices.md` for a standalone run. Persist safe progress on resume. For imports, proposed directives remain in their jobs; record only declared session-schema fields and use `detail` for additional context:

- fetch mode and target date or historical range;
- required commodities, source coverage and dry-run job count;
- terminal completion state and exit code, start/end times and duration;
- each emitted/redundant/skipped/failed/unaccounted job;
- sanitized stderr, warnings/errors and actual quote dates;
- generated panel approval and validation when present; preserve these fields during scoped edits.

Fetch outcome and ledger validation are separate. The Prices skill owns review and writing. Optional `approval` is panel-managed; chat approval stays in conversation. `validation` is generated by the shared validation operation and must not be copied or edited by the agent. A passed review-stage report checks proposals; only a passed written-stage report checks their presence in the ledger.

Required commodities without sources remain skipped/blocking follow-ups. Keep credentials, account identifiers and copied shell snippets out of records. A price-stage failure does not reverse a completed statement. Report a fetch success with failed ledger validation as unfinished; do not append duplicate prices when resuming.
