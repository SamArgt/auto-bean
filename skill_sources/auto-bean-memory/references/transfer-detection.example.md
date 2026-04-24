# Transfer Detection Memory Example

Destination: `.auto-bean/memory/transfer_detection.json`

Use this memory type when an approved workflow learns a reusable transfer pattern between two accounts or between a statement-side transaction and an existing ledger counterpart.

Example record:

```json
{
  "schema_version": 1,
  "memory_type": "transfer_detection",
  "source": {
    "workflow": "auto-bean-apply",
    "statement_source": "statements/parsed/example-checking-2026-04.json",
    "evidence": "user confirmed likely transfer finding"
  },
  "decision": {
    "outflow_match": {
      "account": "Assets:Bank:Example:Checking",
      "payee_contains": "Example Savings Transfer"
    },
    "inflow_match": {
      "account": "Assets:Bank:Example:Savings",
      "payee_contains": "Transfer From Checking"
    },
    "date_tolerance_days": 2,
    "amount_must_match": true
  },
  "scope": {
    "institution": "Example Bank",
    "currency": "USD"
  },
  "confidence": 0.92,
  "review_state": "approved",
  "created_at": "2026-04-24T10:20:00Z",
  "updated_at": "2026-04-24T10:20:00Z",
  "audit": {
    "originating_workflow": "auto-bean-apply",
    "run_id": "apply-20260424T102000Z"
  }
}
```

Transfer memory should suggest review candidates only. It must not silently merge, net, or delete postings.
