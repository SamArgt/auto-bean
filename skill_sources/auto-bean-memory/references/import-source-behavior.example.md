# Import Source Behavior Memory Example

Index destination: `.auto-bean/memory/import_sources/index.json`

Source destination: `.auto-bean/memory/import_sources/<source_slug>.json`

Use this memory type when an approved workflow learns source-specific statement behavior that is useful for processing future statements: file naming, parser hints, column semantics, account identity hints, statement-shape quirks, or reusable import handling rules.

The records should contain practical information that helps `$auto-bean-process` recognize the source and normalize raw evidence without replacing current evidence. Keep processing guidance concrete: expected format, stable headers or sections, date/amount semantics, raw-statement account owner and account names, source identity checks, parser warnings that are safe to expect, and conditions that should block reuse.

Read the index before reading or writing a source file.

Example index file:

```json
{
  "schema_version": 1,
  "memory_type": "import_source_behavior_index",
  "sources": [
    {
      "source_slug": "example-bank-checking-1234",
      "path": "example-bank-checking-1234.json",
      "institution": "Example Bank",
      "account_owner": "Sam Example",
      "account_names": ["Everyday Checking", "Example Bank Everyday Checking"],
      "account_hint": "checking ending 1234",
      "statement_patterns": ["example_bank_checking_*.csv"],
      "updated_at": "2026-04-24T10:15:00Z"
    }
  ]
}
```

Example source file:

```json
{
  "schema_version": 1,
  "memory_type": "import_source_behavior",
  "source_slug": "example-bank-checking-1234",
  "source_identity": {
    "institution": "Example Bank",
    "account_owner": "Sam Example",
    "account_names": ["Everyday Checking", "Example Bank Everyday Checking"],
    "account_hint": "checking ending 1234",
    "currency": "USD"
  },
  "records": [
    {
      "schema_version": 1,
      "memory_type": "import_source_behavior",
      "source": {
        "workflow": "auto-bean-import",
        "statement_source": "statements/raw/example_bank_checking_2026_04.csv",
        "evidence": "approved import finalization"
      },
      "decision": {
        "date_column": "Posted Date",
        "amount_column": "Amount",
        "description_column": "Description",
        "amount_sign": "negative means outflow"
      },
      "scope": {
        "institution": "Example Bank",
        "account_owner": "Sam Example",
        "account_names": ["Everyday Checking", "Example Bank Everyday Checking"],
        "account_last4": "1234",
        "file_type": "csv"
      },
      "confidence": 0.96,
      "review_state": "approved",
      "created_at": "2026-04-24T10:15:00Z",
      "updated_at": "2026-04-24T10:15:00Z",
      "audit": {
        "originating_workflow": "auto-bean-import",
        "run_id": "import-20260424T101500Z"
      }
    }
  ]
}
```

Keep one source file per statement source. Update `index.json` whenever lookup metadata changes.
