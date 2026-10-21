# Governed memory examples

These synthetic examples illustrate the fixed memory categories. Example hashes are placeholders: real records cite the explicit approval instruction or panel confirmation, generated validation digest and timestamp. Read the relevant section only. Destinations are relative to `.auto-bean/memory/`. Record eligibility, ID retention and update rules live in [the memory skill](../SKILL.md); these examples are not permission to save a rule.

The first five sections show one record inside the file’s `records` array. The source section shows the complete index and source document; the final section shows a workspace Markdown correction.

## Account mapping

Destination: `account_mappings.json`. A reviewed external account identity maps to one ledger account. Keep institution, owner, suffix and currency scope; this does not establish category or transfer behavior.


```json
{
  "record_id": "example-account-mapping.example",
  "schema_version": 1,
  "memory_type": "account_mapping",
  "source": {
    "workflow": "auto-bean-import",
    "statement_source": "statements/parsed/example-checking-2026-04.json",
    "evidence": "Account mapping accepted in explicitly approved parsed decisions verified in the ledger."
  },
  "decision": {
    "external_account_label": "Example Bank Everyday Checking ending 1234",
    "statement_account_owner": "Sam Example",
    "statement_account_names": [
      "Everyday Checking",
      "Example Bank Everyday Checking"
    ],
    "beancount_account": "Assets:Bank:Example:Checking"
  },
  "scope": {
    "institution": "Example Bank",
    "account_owner": "Sam Example",
    "account_names": [
      "Everyday Checking",
      "Example Bank Everyday Checking"
    ],
    "account_last4": "1234",
    "currency": "USD"
  },
  "confidence": 0.98,
  "review_state": "approved",
  "created_at": "2026-04-24T10:00:00Z",
  "updated_at": "2026-04-24T10:00:00Z",
  "audit": {
    "originating_workflow": "auto-bean-import",
    "run_id": "categorize-20260424T100000Z",
    "session_id": "example-reviewed-import",
    "approval_evidence": "User approved the current decisions in the import conversation.",
    "review_digest": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "validated_at": "2026-04-24T09:55:00Z"
  }
}
```

## Category mapping

Destination: `category_mappings.json`. A reviewed merchant or memo pattern maps to a posting account. Keep concrete matching criteria and approval evidence.


```json
{
  "record_id": "example-category-mapping.example",
  "schema_version": 1,
  "memory_type": "category_mapping",
  "source": {
    "workflow": "auto-bean-import",
    "statement_source": "statements/parsed/example-card-2026-04.json",
    "evidence": "Specific merchant/category decision accepted in explicitly approved parsed decisions verified in the ledger."
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
    "originating_workflow": "auto-bean-import",
    "run_id": "categorize-20260424T100500Z",
    "session_id": "example-reviewed-import",
    "approval_evidence": "User approved the current decisions in the import conversation.",
    "review_digest": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "validated_at": "2026-04-24T09:55:00Z"
  }
}
```

## Transfer detection

Destination: `transfer_detection.json`. A reviewed relationship suggests transfer matches; it never authorizes silent merging, netting or deletion.


```json
{
  "record_id": "example-transfer-detection.example",
  "schema_version": 1,
  "memory_type": "transfer_detection",
  "source": {
    "workflow": "auto-bean-import",
    "statement_source": "statements/parsed/example-checking-2026-04.json",
    "evidence": "Resolved linked transfer was explicitly approved and validated once in the ledger with both source identities."
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
    "originating_workflow": "auto-bean-import",
    "run_id": "categorize-20260424T102000Z",
    "session_id": "example-reviewed-import",
    "approval_evidence": "User approved the current decisions in the import conversation.",
    "review_digest": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "validated_at": "2026-04-24T09:55:00Z"
  }
}
```

## Deduplication decision

Destination: `deduplication_decisions.json`. A reusable duplicate or non-duplicate decision retains its review trail. Surface the evidence before suppressing any posting.


```json
{
  "record_id": "example-deduplication-decision.example",
  "schema_version": 1,
  "memory_type": "deduplication_decision",
  "source": {
    "workflow": "auto-bean-import",
    "statement_source": "statements/parsed/example-card-2026-04.json",
    "evidence": "Approved duplicate disposition passed coverage validation against the actual existing transaction."
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
    "originating_workflow": "auto-bean-import",
    "run_id": "categorize-20260424T102500Z",
    "session_id": "example-reviewed-import",
    "approval_evidence": "User approved the current decisions in the import conversation.",
    "review_digest": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "validated_at": "2026-04-24T09:55:00Z"
  }
}
```

## Commodity price source

Destination: `commodity_price_sources.json`. Use `method_type: beanprice` when reliable, or `web_search` for a narrow authoritative source. Do not store credentials, account numbers or shell snippets.


```json
{
  "record_id": "example-commodity-price-source.example",
  "schema_version": 1,
  "memory_type": "commodity_price_source",
  "source": {
    "workflow": "auto-bean-prices",
    "ledger_commodity": "AAPL",
    "evidence": "Verified commodity/source identity, successful accounted run and separately approved price directives verified in the ledger."
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
    "run_id": "prices-20260512T100500Z",
    "session_id": "example-reviewed-import",
    "approval_evidence": "User approved the current decisions in the import conversation.",
    "review_digest": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "validated_at": "2026-05-12T10:00:00Z"
  }
}
```

## Import source behavior

Destination: `import_sources/<source_slug>.json`. Read `import_sources/index.json` first. Keep one source file per matched source and update the index when lookup metadata changes. Source observations must not become inferred account mappings or ambiguous sign/date rules.


Index (`import_sources/index.json`):

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


Indexed source document:

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
      "record_id": "example-source-columns",
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

## Workspace Markdown

Destination: `MEMORY.md`, maintained by the main thread. This example is a current explicit user correction: “Use Europe/Paris for report dates and show EUR amounts with two decimal places.” It changes presentation preferences, so it belongs in Markdown rather than a category or price-source rule.

Before:

```markdown
## User Preferences

- Show report dates in UTC.
- Use concise English explanations.
```

After:

```markdown
## User Preferences

- Show report dates in Europe/Paris and EUR amounts with two decimal places.
- Use concise English explanations.
```

The main thread replaces the conflicting bullet and retains the unrelated language preference. If the section instead contains only “No durable preferences recorded yet,” replace that placeholder. An inferred timezone from a statement address would not justify replacing the explicit UTC preference.

A worker returns the exact before/after bullet above, section `User Preferences`, and evidence “current user request, 2026-04-24”; it does not edit the file. The main thread verifies the request, applies the scoped patch, rereads the section and reports the change. No import status or memory-outcome field is added.
