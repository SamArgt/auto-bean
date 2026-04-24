# Account Mapping Memory Example

Destination: `.auto-bean/memory/account_mappings.json`

Use this memory type when an approved workflow learns that a statement-side account, counterparty account, card, or externally named account maps to a Beancount account.

Example record:

```json
{
  "schema_version": 1,
  "memory_type": "account_mapping",
  "source": {
    "workflow": "auto-bean-apply",
    "statement_source": "statements/parsed/example-checking-2026-04.json",
    "evidence": "approved import finalization"
  },
  "decision": {
    "external_account_label": "Example Bank Everyday Checking ending 1234",
    "beancount_account": "Assets:Bank:Example:Checking"
  },
  "scope": {
    "institution": "Example Bank",
    "account_last4": "1234",
    "currency": "USD"
  },
  "confidence": 0.98,
  "review_state": "approved",
  "created_at": "2026-04-24T10:00:00Z",
  "updated_at": "2026-04-24T10:00:00Z",
  "audit": {
    "originating_workflow": "auto-bean-apply",
    "run_id": "apply-20260424T100000Z"
  }
}
```

Keep account mappings narrow. Do not infer broad category, payee, or transfer behavior from an account mapping alone.
