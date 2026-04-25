# Clarification Outcome Memory Example

Destination: `.auto-bean/memory/clarification_outcomes.json`

Use this memory type when a user answer resolves an ambiguous or unfamiliar pattern and the user approves reusing that answer later.

Example record:

```json
{
  "schema_version": 1,
  "memory_type": "clarification_outcome",
  "source": {
    "workflow": "auto-bean-categorize",
    "statement_source": "statements/parsed/example-checking-2026-04.json",
    "evidence": "user answered bounded clarification question"
  },
  "decision": {
    "question": "Should Example Payroll Reversal be treated as income reversal or expense refund?",
    "answer": "Treat it as income reversal for this employer pattern.",
    "reuse_rule": {
      "payee_contains": "Example Payroll Reversal",
      "posting_account": "Income:Salary"
    }
  },
  "scope": {
    "institution": "Example Bank",
    "counterparty": "Example Payroll"
  },
  "review_state": "explicitly_approved",
  "created_at": "2026-04-24T10:30:00Z",
  "updated_at": "2026-04-24T10:30:00Z",
  "audit": {
    "originating_workflow": "auto-bean-categorize",
    "run_id": "categorize-20260424T103000Z"
  }
}
```

Only store clarification outcomes when the user explicitly approves reuse. A clarification that unblocks one transaction is not automatically durable memory.
