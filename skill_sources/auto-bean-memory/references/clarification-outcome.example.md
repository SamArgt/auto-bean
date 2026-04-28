# Clarification Outcome Memory Example

Destination: `.auto-bean/memory/clarification_outcomes.json`

Use this memory type when an answer recorded in a statement-scoped artifact resolves an ambiguous or unfamiliar pattern and the user approves reusing the resulting rule later. Keep the original question and answer in the originating artifact; durable memory stores only the reusable outcome and an artifact reference.

Example record:

```json
{
  "schema_version": 1,
  "memory_type": "clarification_outcome",
  "source": {
    "workflow": "auto-bean-categorize",
    "statement_source": "statements/parsed/example-checking-2026-04.json",
    "evidence": "bounded clarification outcome recorded in statement artifact",
    "originating_artifact": ".auto-bean/artifacts/categorize/example-checking-2026-04--categorize.md",
    "question_id": "Q3"
  },
  "decision": {
    "clarified_rule": "Treat Example Payroll Reversal as an income reversal for this employer pattern.",
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

Only store clarification outcomes when the user explicitly approves reuse. A clarification that unblocks one transaction is not automatically durable memory. Do not copy original question or answer text into memory; link to the artifact and store the approved reusable rule.
