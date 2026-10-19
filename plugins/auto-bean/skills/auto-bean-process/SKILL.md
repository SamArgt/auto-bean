---
name: auto-bean-process
description: Normalize one raw PDF, CSV, XLSX, or XLS assigned by auto-bean-import. Use only for its raw-to-parsed stage; return evidence, artifacts, blockers, and proposed status.
---

Read [plugin execution](../../references/plugin-execution.md), [workflow rules](../../references/workflow-rules.md), [state validation](../../references/state-validation.md), and relevant workspace `.auto-bean/memory/MEMORY.md` context. Work only on the assigned source, fingerprint, expected parsed target, shared artifact prefix, existing artifacts/answers, and supplied status snapshot. Do not discover other inputs, invoke categorization, mutate ledger files, or edit shared status.

## Preparation and extraction

1. Confirm the safe source is under `statements/raw/`, exists, and is PDF, CSV, XLSX, or XLS. Compute SHA-256 and compare supplied retry state. Read [memory rules](../../references/memory-access-rules.md) only when selecting/reusing source hints; use the import-source index first and narrowly matching source files only. Memory never overrides source evidence.
2. Prepare extraction separately from per-document timeouts:

   ```sh
   sh "$AUTO_BEAN_PLUGIN/runtime/launch.sh" ensure-runtime --workspace "$AUTO_BEAN_WORKSPACE" --extraction
   ```

   This may install Docling/CPU model dependencies. PDF models can also download on first use; prefetch the required models using the installed Docling version's documented model command before timing extraction, or record a first-use preparation blocker. Model preparation has its own bounded 10-minute budget and is not a statement parse attempt. Check official Docling docs through Context7 when commands or support are unclear.
3. Run `auto_bean docling <assigned-source> --to json --output <unique-.auto-bean/tmp/directory>`. Time the extraction itself: PDF 120 seconds, CSV/Excel 60 seconds. Poll the same running session until terminal exit. Preparation failure never becomes a parser crash or consumes source retries.
4. Classify failures before retrying. Timeout/interruption/transient filesystem IO permits one retry with fresh output. Nonzero parser crash, malformed output, missing evidence, encrypted/corrupt/missing source, or unsupported format is not retried unless clearly transient. Scanned/textless PDFs may use supported local OCR; block if trustworthy extraction is unavailable. Never guess.
5. Persist command, timeout, attempts, terminal result, sanitized failure summary, output pointer, and repair need in `.auto-bean/artifacts/process/<artifact_prefix>--process.md`. Failure codes are `tool_timeout`, `transient_io_failure`, `parser_crash`, `malformed_parser_output`, `unsupported_format`, `encrypted_or_unreadable_source`, `textless_pdf`, `missing_source`, or `tool_unavailable`.

## Normalized evidence

Use the [parsed example](../../references/parsed-statement-output.example.json) and validator schema. New JSON includes `schema_version: 1`, `document_kind`, parser/run metadata, source path/fingerprint/format, parsed timestamp, process artifact pointer, statement metadata/accounts, and extracted records. Keep `snake_case` keys and decimal strings.

`statement` means evidence supplies a statement period/balances; `transaction_export` means a transaction list without those facts. Preserve missing values as absent/null; do not manufacture periods, balances, ownership, or account identity. Every record has a stable source row `record_id`, `source_reference`, account reference, transaction date, description, signed amount, and currency. Accounts have unique stable `account_id` values. A multi-account row without a trustworthy account match blocks processing. Preserve IDs across reparses of the same source; new parse runs get new versioned output paths, not new identities for the same rows.

Validate normalized output before handing it downstream. Keep extraction warnings, manual questions/answers, and source-memory attribution in the process artifact, not parsed JSON/status. Delete temporary extraction output only after normalized output is safely persisted and validated, unless debugging needs it. Use [bounded parsed reading](../../references/parsed-statement-jq-reading.md) for existing/large evidence.

## Return to import

Persist safe evidence and stable question IDs; never ask users directly. Return source fingerprint, parsed path/run ID, process artifact, evidence-quality result, blockers/questions, safe progress, memory attribution/suggestions, and one proposed status:

- `process_blocked`: missing/untrustworthy evidence or required manual repair.
- `process_review`: normalized evidence exists but warnings need review.
- `account_review`: valid evidence without pending process questions.

Import alone applies the proposal to the latest status index. Return retry metadata for the current source fingerprint; after two extraction attempts propose `manual_resolution_required: true`. A changed source starts a new retry count. Preparation failures do not increment extraction attempts. Unresolved blockers never become durable memory.
