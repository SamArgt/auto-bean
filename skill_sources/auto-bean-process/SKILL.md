---
name: auto-bean-process
description: Process exactly one assigned raw statement file into normalized parsed evidence through the local Docling CLI. Use as the `$auto-bean-import` raw-to-parsed sub-agent stage. It owns parsing, process artifacts, per-input parse status updates, and processing memory suggestions; `$auto-bean-import` owns work discovery, first-seen accounts, posting workflows, and finalization.
---

Use this only for the raw-to-parsed stage assigned by `$auto-bean-import`.

Inputs from `$auto-bean-import`:

- relevant `.auto-bean/memory/MEMORY.md` context
- one raw statement path under `statements/raw/`
- the matching `statements/import-status.yml` entry when one exists
- the expected parsed-output path or naming rule
- the shared raw-statement artifact prefix to use for this source's process, categorize, and import artifacts
- any relevant source-memory hint already selected for this input

MUST read before acting:

- `.auto-bean/memory/MEMORY.md`
- `.agents/skills/shared/workflow-rules.md`
- `.agents/skills/shared/parsed-statement-output.example.json`
- `.agents/skills/shared/import-status-reading.md` before reading or updating a large `statements/import-status.yml`

Read when needed:

- `.agents/skills/shared/import-status.example.yml` MUST be read when creating new status fields, auditing schema shape, or reconciling an unexpected status entry before updating it.
- `.agents/skills/shared/parsed-statement-jq-reading.md` MUST be read before inspecting any existing parsed statement JSON, comparing a prior parse to a new parse, or investigating record-count, `account_id`, statement metadata, or multi-account mismatches.
- `.agents/skills/shared/memory-access-rules.md` MUST be read before using, rejecting, correcting, or proposing governed memory hints, including parser, source, account, filename-pattern, or statement-shape hints;
- `.auto-bean/memory/import_sources/index.json`, then the matching indexed `import_source_behavior` memory file, MUST be read when source identity, institution, raw-statement account owner, raw-statement account names, account hints, statement shape, filename pattern, or fingerprint suggests a narrow match. Do not open non-matching source files.

Workflow:

1. Confirm the assigned scope:
   - process only the assigned raw statement path, status entry, expected parsed-output path or rule, and shared artifact prefix
   - do not scan `statements/raw/` for more work
   - do not invoke `$auto-bean-categorize`
   - keep raw inputs in `statements/raw/`, parsed outputs in `statements/parsed/`, parse state in `statements/import-status.yml`, and the process artifact in `.auto-bean/artifacts/process/`
2. Plan from this input:
   - use `.auto-bean/memory/MEMORY.md` only for relevant user profile, main-account, preference, correction, and general source context
   - verify the source exists and is `.pdf`, `.csv`, `.xlsx`, or `.xls`
   - compute a deterministic fingerprint such as `sha256`
   - compare the fingerprint to the supplied status entry, if any
   - look for applicable `import_source_behavior` memory through `.auto-bean/memory/import_sources/index.json`, opening only matching indexed source files
   - use source-behavior memory only for processing-relevant facts such as parser hints, statement shape, column semantics, filename/source identity patterns, raw-statement account owner and account name patterns, account identity hints, and reusable import handling checks
3. Parse with the local Docling CLI:
   - prefer `./.venv/bin/docling` directly on the assigned source; if it is unavailable but `uv run docling` works in this workspace, use `uv run docling` with the same arguments
   - enforce an execution timeout for each Docling attempt: PDF `120s`; CSV, XLSX, and XLS `60s`
   - classify failures before retrying:
     - transient execution failure: timeout, interrupted process, temporary filesystem read error, or temp-output write race; retry once with a fresh temp output path, then set `process_blocked` if it fails again
     - parser crash: nonzero Docling exit, exception traceback, malformed JSON output, or output missing required evidence; do not retry unless the failure text clearly names a transient IO condition
     - unsupported or unsafe input: unsupported extension, encrypted/password-protected file, scanned or textless PDF, corrupt file, missing source, unavailable Docling/dependency, or command path unavailable through both supported paths; do not retry
   - map unrecovered failures deterministically to `process_blocked`: record `last_process_failure_reason` as `tool_timeout`, `transient_io_failure`, `parser_crash`, `malformed_parser_output`, `unsupported_format`, `encrypted_or_unreadable_source`, `textless_pdf`, `missing_source`, or `tool_unavailable`
   - include the timeout, attempt count, command path used, failure class, concise stderr/stdout summary, temp output path if any, and required manual repair or dependency action in the process artifact
   - request JSON output into a unique temp path under `.auto-bean/tmp/`
   - default command patterns:
     - PDF: `./.venv/bin/docling statements/raw/bank/jan-2026.pdf --to json --output .auto-bean/tmp/docling-20260411T090000Z-jan-2026-1ef7e13f`
     - CSV: `./.venv/bin/docling statements/raw/cards/2026-01.csv --to json --output .auto-bean/tmp/docling-20260411T090000Z-2026-01-csv-a82c91d4`
     - Excel: `./.venv/bin/docling statements/raw/brokerage/holdings-2026-01.xlsx --to json --output .auto-bean/tmp/docling-20260411T090000Z-holdings-2026-01-6cb2e40a`
   - translate Docling output into the normalized parsed-output contract
   - delete temp artifacts after the normalized output is safely written unless active debugging needs them
   - if unsure about Docling CLI flags, supported formats, or dependency behavior, use Context7 before adapting the command
   - if Docling or a required local dependency is unavailable through both supported command paths, report the concrete failure and stop for this file
   - if a scanned or textless PDF cannot be extracted, do not guess; set `process_blocked` and record the issue for `$auto-bean-import`
4. Persist normalized evidence:
   - write one deterministic JSON artifact for this source or parse run under `statements/parsed/`
   - include only necessary parse metadata and extracted evidence such as `parse_run_id`, `source_file`, `source_fingerprint`, `source_format`, parser identifier, `parsed_at`, process artifact path, `account_owner`, `account_names`, `statement_metadata`, and extracted records
   - populate `account_owner`, `account_names`, and `statement_metadata` only from raw-statement evidence; use `null`, `[]`, or omitted nested fields when the statement does not expose values clearly, and record extraction ambiguity in the process artifact
   - when present, use `statement_metadata` for statement-scoped facts such as institution name, statement period, and statement issue date; put account-specific facts under `statement_metadata.accounts[]`, including a stable parsed `account_id`, account identifiers, account type, primary currency, opening/closing/available balances, reported record counts, and balance reconciliation checks
   - set `account_id` on every extracted record to point to the matching `statement_metadata.accounts[]` entry; if a record's account cannot be identified in a multi-account statement, apply the shared fail-closed invariant with `process_blocked` instead of assigning it by guess
   - when a multi-account statement has missing, duplicated, or mismatched `account_id` values, read `.agents/skills/shared/parsed-statement-jq-reading.md` before continuing and block rather than guessing if the mismatch cannot be resolved from statement evidence
   - keep all contract keys in `snake_case`
   - on re-parse, write a new versioned output and refresh only this statement's status entry
5. Update only this input's status:
   - set `process_blocked` when no trustworthy parsed evidence exists yet or manual follow-up is required before parsing is trustworthy
   - set `account_review` when normalized output is written and no warnings require `$auto-bean-import` review
   - set `process_review` when normalized output is written but warnings need `$auto-bean-import` review before account inspection
   - allowed status updates from this stage are `process_blocked`, `process_review`, and `account_review`; all later workflow statuses are advanced by `$auto-bean-import`
   - record only operational status data: current status, source fingerprint, updated timestamp, parsed statement path, stage artifact paths, retry metadata, and compact user-input flags; keep warning, question, and answer payloads in the process artifact only
   - when setting `process_blocked`, increment `process_attempts` for the current source fingerprint, set `last_process_failure_reason`, and set `manual_resolution_required: true` once the current-fingerprint attempt count reaches 2
   - when the source fingerprint changes, start a new retry count for that fingerprint while preserving any prior failure context that remains useful in warnings or blocking issues
6. Continue through safe raw-to-parsed work while collecting questions:
   - follow the shared question-handling rules
   - keep progressing through every deterministic parsing, normalization, status, and evidence-quality step that does not require guessing
   - write one deterministic process artifact under `.auto-bean/artifacts/process/`, using the shared raw-statement artifact prefix from `$auto-bean-import`, such as `.auto-bean/artifacts/process/<artifact_prefix>--process.md`
   - use that process artifact for process-stage questions, manual extraction notes, source-memory reuse attribution, and processing-related `memory_suggestions`
   - reflect only the process artifact path in the parsed output and status entry; do not embed warning, question, or answer payloads outside the process artifact
   - when user input is required, never ask the user directly; return only persisted question ids, the process artifact path, and operational blocker flags to `$auto-bean-import` so the orchestrator can ask and update or resume the intermediate statement
   - collect eligible reusable learning into a `Memory Suggestions` section of the process artifact, even when there are no user questions
7. Return control to `$auto-bean-import`:
   - assigned source path and source fingerprint
   - parsed output path and parse run id
   - status change for this input
   - whether warnings or blockers exist, retry metadata, and evidence-quality result, with warning details kept in the process artifact
   - memory reuse attribution if governed memory influenced parsing or source handling
   - every process artifact written under `.auto-bean/artifacts/process/`, with question ids, affected intermediate-statement fields, source-memory attribution, and processing-related memory suggestions
  

Guardrails:

- Follow the shared workflow rules for ownership boundaries, status management, question handling, sub-agent handoff, compact returns, and memory use.
- Do not claim success when evidence is ambiguous, structure is risky, or validation fails.
- Do not process unassigned statements.
