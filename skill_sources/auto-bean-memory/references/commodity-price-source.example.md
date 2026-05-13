# Commodity Price Source Memory Example

Destination: `.auto-bean/memory/commodity_price_sources.json`

Use this memory type when an approved price-update workflow learns how a Beancount commodity should be priced from an external source.

Example record:

```json
{
  "schema_version": 1,
  "memory_type": "commodity_price_source",
  "source": {
    "workflow": "auto-bean-prices",
    "ledger_commodity": "AAPL",
    "evidence": "user approved Yahoo Finance source during price review"
  },
  "decision": {
    "commodity": "AAPL",
    "quote_currency": "USD",
    "method_type": "beanprice",
    "source": "USD:yahoo/AAPL"
  },
  "scope": {
    "commodity": "AAPL",
    "asset_class": "stock",
    "region": "US"
  },
  "confidence": 0.9,
  "review_state": "approved",
  "created_at": "2026-05-12T10:05:00Z",
  "updated_at": "2026-05-12T10:05:00Z",
  "audit": {
    "originating_workflow": "auto-bean-prices",
    "run_id": "prices-20260512T100500Z"
  }
}
```

Allowed `method_type` values are `beanprice` and `web_search`. Prefer `beanprice`; use `web_search` only when no reliable beanprice source is available yet. Keep queries narrow, source-specific, and reviewable; do not store API keys, session tokens, account numbers, or shell snippets.
