# Deduplication Decision Memory Example

Destination: `.auto-bean/memory/deduplication_decisions.json`

Use this memory type when an approved workflow learns a reusable duplicate-detection or non-duplicate rule.

Example record:

```json
{
  "schema_version": 1,
  "memory_type": "deduplication_decision",
  "source": {
    "workflow": "auto-bean-categorize",
    "statement_source": "statements/parsed/example-card-2026-04.json",
    "evidence": "user resolved possible_duplicate finding"
  },
  "decision": {
    "match": {
      "same_external_id": true,
      "same_amount": true,
      "date_tolerance_days": 0
    },
    "outcome": "treat_as_duplicate",
    "action": "do_not_create_second_posting"
  },
  "scope": {
    "institution": "Example Card",
    "file_type": "csv"
  },
  "confidence": 0.94,
  "review_state": "approved",
  "created_at": "2026-04-24T10:25:00Z",
  "updated_at": "2026-04-24T10:25:00Z",
  "audit": {
    "originating_workflow": "auto-bean-categorize",
    "run_id": "categorize-20260424T102500Z"
  }
}
```

Deduplication memory should preserve the review trail. Do not delete or suppress candidate transactions without surfacing the reason.
