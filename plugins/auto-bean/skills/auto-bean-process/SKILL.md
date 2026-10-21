---
name: auto-bean-process
description: Normalize raw PDF, CSV, XLSX, or XLS sources in a statement group assigned by auto-bean-import. Use only for its raw-to-parsed stage; return per-source evidence, blockers, and one proposed group status.
---

Read [common guidance](../../references/common.md) once, then the import contract's [state](../../references/import-review.md#state-and-validation) and [ownership](../../references/common.md#ownership) sections. Work as the processing subagent for the assigned group. Apply the steps below separately to each assigned source, fingerprint and retry context in the supplied session. Use the single assigned group parsed target. Keep attempts and evidence in each source section; return one group status proposal. Continue independent members when one is blocked. Do not discover inputs, categorize, mutate ledger files or edit shared status.

## Preparation and extraction

1. Confirm the safe source is under `statements/raw/`, exists and is PDF, CSV, XLSX or XLS. Compute SHA-256 against supplied retry state. When source hints are needed, read the import-source index first and only matching indexed files.
2. Prepare extraction separately from per-document timeouts:

   ```sh
   sh "$AUTO_BEAN_PLUGIN/runtime/launch.sh" ensure-runtime --workspace "$AUTO_BEAN_WORKSPACE" --extraction
   ```

   Docling/CPU model preparation has a separate 10-minute budget. Prefetch required PDF models with the installed version's documented command before timing extraction, or record a first-use blocker. Check official Docling docs through Context7 when support is unclear. Preparation failures do not consume source attempts.
3. Create the assigned group document only if absent, before extraction, using the [group schema](../../references/schemas/parsed-group.schema.json). Initialize a pending `statements` section for every assigned source, using the embedded [statement schema](../../references/schemas/parsed-v2.schema.json); on resume preserve its existing decisions, answers and evidence. Run `auto_bean docling <assigned-source> --to json --output <unique-.auto-bean/tmp/directory>`; allow 120 seconds for PDF or 60 seconds for CSV/Excel. Poll the same session until terminal exit.
4. Timeout/interruption/transient filesystem IO permits one retry with fresh output. Do not retry crashes, malformed/missing evidence, encrypted/corrupt/missing sources or unsupported formats unless clearly transient. Supported local OCR may handle scanned/textless PDFs; otherwise block rather than guess.
5. In the current source section, persist attempts, terminal outcome, extraction evidence, sanitized failure reason, output pointer, warnings and repair need in `review.processing`. Required input uses needs_input, suggestions and failure_reason/evidence there. Use the schema's failure code: `tool_timeout`, `transient_io_failure`, `parser_crash`, `malformed_parser_output`, `unsupported_format`, `encrypted_or_unreadable_source`, `textless_pdf`, `missing_source` or `tool_unavailable`.

## Normalization and return

Use the [parsed example](../../references/parsed-statement-output.example.json) to illustrate the [state contract](../../references/import-review.md#state-and-validation). `statement` supplies a period/balances; `transaction_export` is a transaction list without those facts. Do not manufacture missing periods, balances, ownership or account identity. A multi-account row without a trustworthy account match blocks processing.

Preserve stable account/row IDs and source references across reparses. Edit extracted facts and processing outcomes directly, preserving existing inline decisions and answers. If corrected evidence changes an earlier decision, return affected IDs for the owning stage to recheck. Complete extraction needs parser/run metadata and timestamp. Pending/failed extraction may have empty evidence arrays and never enters accounting stages.

Check the source-to-parsed contract and schema before handing evidence downstream; Import runs shared review validation when decisions are ready. Keep processing input/warnings and relevant source-normalization evidence in review.processing; later memory learning uses those facts directly. Delete temporary output only after safely publishing validated evidence unless debugging requires retention. Use [bounded inspection](../../references/import-review.md#reading-evidence) for large documents.

Return per-source fingerprints, run IDs, outcomes, blockers and safe progress, the shared parsed path and one group status proposal. Any blocked member holds the group; otherwise use the least advanced member outcome:

- `process_blocked`: missing/untrustworthy evidence or manual repair.
- `process_review`: normalized evidence exists but warnings need review.
- `account_review`: valid evidence with no unresolved processing input.

Persist extraction input in each source section's `review.processing`; Import asks the user and applies status. Return attempts for the current fingerprint; after two extraction attempts propose `manual_resolution_required: true`. A changed source starts a new retry count.
