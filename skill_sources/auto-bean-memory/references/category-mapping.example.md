# Category Mapping Memory Example

Destination: `.auto-bean/memory/category_mappings.json`

Use this memory type when an approved workflow learns that a payee, merchant pattern, memo pattern, or transaction description maps to an expense, income, asset, liability, or equity category.

Example record:

```json
{
  "schema_version": 1,
  "memory_type": "category_mapping",
  "source": {
    "workflow": "auto-bean-categorize",
    "statement_source": "statements/parsed/example-card-2026-04.json",
    "evidence": "user approved categorization during final review"
  },
  "decision": {
    "match": {
      "payee_contains": "Example Transit",
      "memo_contains": "monthly pass"
    },
    "posting_account": "Expenses:Transport:PublicTransit"
  },
  "scope": {
    "institution": "Example Card",
    "currency": "USD"
  },
  "confidence": 0.9,
  "review_state": "approved",
  "created_at": "2026-04-24T10:05:00Z",
  "updated_at": "2026-04-24T10:05:00Z",
  "audit": {
    "originating_workflow": "auto-bean-categorize",
    "run_id": "categorize-20260424T100500Z"
  }
}
```

Keep matching criteria concrete. Do not store vague preferences such as "usually groceries" without source evidence and approval.
