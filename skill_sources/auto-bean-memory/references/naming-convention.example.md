# Naming Convention Memory Example

Destination: `.auto-bean/memory/naming_conventions.json`

Use this memory type when an approved workflow learns a stable naming rule for payees, narrations, links, tags, account names, or imported metadata normalization.

Example record:

```json
{
  "schema_version": 1,
  "memory_type": "naming_convention",
  "source": {
    "workflow": "auto-bean-apply",
    "statement_source": "statements/parsed/example-card-2026-04.json",
    "evidence": "user approved normalized payee naming"
  },
  "decision": {
    "raw_pattern": "EXAMPLE COFFEE STORE #*",
    "normalized_payee": "Example Coffee",
    "normalization_rule": "strip store number suffix from card statement payee"
  },
  "scope": {
    "institution": "Example Card",
    "applies_to": "payee"
  },
  "confidence": 0.95,
  "review_state": "approved",
  "created_at": "2026-04-24T10:10:00Z",
  "updated_at": "2026-04-24T10:10:00Z",
  "audit": {
    "originating_workflow": "auto-bean-apply",
    "run_id": "apply-20260424T101000Z"
  }
}
```

Naming memory should standardize display and ledger text only. Do not use it to choose accounts, classify transfers, or resolve duplicates.
