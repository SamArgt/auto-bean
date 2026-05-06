# Sub-Agent Return Examples

Purpose: concrete examples for sub-agent stages reporting back to `$auto-bean-import`.

Use the same compact style even when running serially instead of through a sub-agent. Use empty lists or `null` for fields that do not apply. Full warning, question, answer, reconciliation, and analysis payloads stay in the owning artifact.

## Process Example

```yaml
assigned_path: statements/raw/checking/jan-2026.pdf
source_fingerprint: sha256:1ef7e13f...
parsed_output: statements/parsed/checking-jan-2026--1ef7e13f--20260411T090000Z.json
parse_run_id: process-20260411T090000Z
status_update:
  current_status: account_review
  parsed_statement: statements/parsed/checking-jan-2026--1ef7e13f--20260411T090000Z.json
artifacts:
  process: .auto-bean/artifacts/process/checking-jan-2026--process.md
blockers: []
pending_questions: []
safe_work_completed:
  - normalized 42 transaction rows
  - extracted opening and closing balances for account acct-checking-001
memory_suggestions:
  - type: import_source_behavior
    summary: Statement filename and layout identify Example Bank checking PDFs.
validation:
  parser: docling
  result: passed
```

## Process Blocked Example

```yaml
assigned_path: statements/raw/card/mar-2026.pdf
source_fingerprint: sha256:7ad0...
parsed_output: null
parse_run_id: process-20260411T093000Z
status_update:
  current_status: process_blocked
  process_attempts: 2
  manual_resolution_required: true
artifacts:
  process: .auto-bean/artifacts/process/card-mar-2026--process.md
blockers:
  - id: process-blocker-1
    summary: PDF appears scanned and textless; no trustworthy parsed evidence.
pending_questions:
  - id: process-q1
    artifact: .auto-bean/artifacts/process/card-mar-2026--process.md
safe_work_completed:
  - fingerprinted source file
memory_suggestions: []
validation:
  parser: docling
  result: failed
```

## Categorize Example

```yaml
assigned_path: statements/parsed/checking-jan-2026--1ef7e13f--20260411T090000Z.json
status_update:
  current_status: categorize_review
artifacts:
  categorize: .auto-bean/artifacts/categorize/checking-jan-2026--categorize.md
blockers: []
pending_questions: []
safe_work_completed:
  - categorized 40 of 42 rows
  - identified two likely transfers for batch review
reconciliation_findings:
  - id: transfer-1
    type: likely_transfer
    artifact: .auto-bean/artifacts/categorize/checking-jan-2026--categorize.md
posting_inputs:
  - id: posting-input-1
    source_row: txn-2026-01-03-001
memory_suggestions:
  - type: category_mapping
    summary: Example Gym monthly debit maps to Expenses:Health:Fitness.
validation: null
```

## Categorize Blocked Example

```yaml
assigned_path: statements/parsed/card-mar-2026--7ad0--20260411T093000Z.json
status_update:
  current_status: categorize_blocked
artifacts:
  categorize: .auto-bean/artifacts/categorize/card-mar-2026--categorize.md
blockers:
  - id: categorize-blocker-1
    summary: Merchant code could be a cash advance or card payment.
pending_questions:
  - id: categorize-q1
    artifact: .auto-bean/artifacts/categorize/card-mar-2026--categorize.md
safe_work_completed:
  - categorized non-ambiguous rows
reconciliation_findings: []
posting_inputs: []
memory_suggestions: []
validation: null
```

## Write Example

```yaml
assigned_path: statements/parsed/checking-jan-2026--1ef7e13f--20260411T090000Z.json
status_update:
  current_status: final_review
artifacts:
  import: .auto-bean/artifacts/import/checking-jan-2026--import.md
blockers: []
pending_questions: []
safe_work_completed:
  - wrote 42 transactions to beancount/checking.beancount
mutation:
  changed_files:
    - beancount/checking.beancount
focused_diff_summary: Added January checking statement transactions with explicit postings.
assumptions: []
validation:
  command: ./scripts/validate-ledger.sh
  result: passed
```

## Write Blocked Example

```yaml
assigned_path: statements/parsed/checking-jan-2026--1ef7e13f--20260411T090000Z.json
status_update:
  current_status: write_blocked
artifacts:
  import: .auto-bean/artifacts/import/checking-jan-2026--import.md
blockers:
  - id: write-blocker-1
    summary: Draft transaction does not validate because account currency is restricted.
pending_questions:
  - id: write-q1
    artifact: .auto-bean/artifacts/import/checking-jan-2026--import.md
safe_work_completed:
  - drafted non-ambiguous transactions
mutation:
  changed_files:
    - beancount/checking.beancount
focused_diff_summary: Draft left in working tree for review and repair.
assumptions: []
validation:
  command: ./scripts/validate-ledger.sh
  result: failed
```

## Memory Example

```yaml
assigned_path: .auto-bean/artifacts/import/checking-jan-2026--import.md
status_update: null
artifacts:
  memory:
    - .auto-bean/memory/import_sources/example_bank_checking.json
blockers: []
pending_questions: []
safe_work_completed:
  - persisted one import-source behavior record
persisted_memory:
  - path: .auto-bean/memory/import_sources/example_bank_checking.json
    summary: Example Bank checking PDFs share filename and layout hints.
skipped_candidates:
  - summary: One category suggestion was too broad for durable memory.
memory_suggestions: []
validation:
  json: passed
```
