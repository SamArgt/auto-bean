---
name: auto-bean-process
description: Process exactly one assigned raw statement file into normalized parsed evidence through the local Docling CLI, recording process questions and memory suggestions for `$auto-bean-import`. Use only as an internal worker stage for `$auto-bean-import`; do not discover import work, derive first-seen accounts, invoke posting workflows, or orchestrate finalization.
---

Use this only for the raw-to-parsed stage assigned by `$auto-bean-import`.

Inputs from `$auto-bean-import`:

- one raw statement path under `statements/raw/`
- the matching `statements/import-status.yml` entry when one exists
- the expected parsed-output path or naming rule
- the shared raw-statement artifact prefix to use for this source's process, categorize, and import artifacts
- any relevant source-memory hint already selected for this input

Read before acting:

- `.agents/skills/shared/memory-access-rules.md` before using governed memory hints
- `.agents/skills/shared/parsed-statement-output.example.json`
- `.agents/skills/shared/parsed-statement-jq-reading.md` before inspecting large parsed statement artifacts
- `.agents/skills/shared/import-status.example.yml`
- `.agents/skills/shared/question-handling-contract.md` before recording process questions
- `.auto-bean/memory/import_sources/index.json`, then the matching indexed `import_source_behavior` memory file when source identity, institution, account hints, statement shape, filename pattern, or fingerprint suggests a narrow match

Workflow:

1. Confirm the assigned scope:
   - process only the assigned raw statement path
   - do not scan `statements/raw/` for more work
   - do not invoke `$auto-bean-categorize`
   - keep raw inputs in `statements/raw/`, parsed outputs in `statements/parsed/`, parse state in `statements/import-status.yml`, and the process artifact in `.auto-bean/artifacts/process/`
2. Plan from this input:
   - verify the source exists and is `.pdf`, `.csv`, `.xlsx`, or `.xls`
   - compute a deterministic fingerprint such as `sha256`
   - compare the fingerprint to the supplied status entry, if any
   - look for applicable `import_source_behavior` memory through `.auto-bean/memory/import_sources/index.json`, opening only matching indexed source files
   - use source-behavior memory only for processing-relevant facts such as parser hints, statement shape, column semantics, filename/source identity patterns, account identity hints, and reusable import handling checks
   - treat selected source memory as advisory guidance only; fail closed if memory is missing, malformed, too broad, stale, or conflicts with current evidence
3. Parse with the local Docling CLI:
   - call `./.venv/bin/docling` directly on the assigned source
   - request JSON output into a unique temp path under `.auto-bean/tmp/`
   - default command patterns:
     - PDF: `./.venv/bin/docling statements/raw/bank/jan-2026.pdf --to json --output .auto-bean/tmp/docling-20260411T090000Z-jan-2026-1ef7e13f`
     - CSV: `./.venv/bin/docling statements/raw/cards/2026-01.csv --to json --output .auto-bean/tmp/docling-20260411T090000Z-2026-01-csv-a82c91d4`
     - Excel: `./.venv/bin/docling statements/raw/brokerage/holdings-2026-01.xlsx --to json --output .auto-bean/tmp/docling-20260411T090000Z-holdings-2026-01-6cb2e40a`
   - translate Docling output into the normalized parsed-output contract
   - delete temp artifacts after the normalized output is safely written unless active debugging needs them
   - if unsure about Docling CLI flags, supported formats, or dependency behavior, use Context7 before adapting the command
   - if Docling or a required local dependency is missing, report the concrete failure and stop for this file
   - if a scanned or textless PDF cannot be extracted, do not guess; leave the statement `ready` and record the issue for `$auto-bean-import`
4. Persist normalized evidence:
   - write one deterministic JSON artifact for this source or parse run under `statements/parsed/`
   - include `parse_run_id`, `source_file`, `source_fingerprint`, `source_format`, parser details, `status`, `parsed_at`, warnings, blocking issues, and extracted records
   - keep all contract keys in `snake_case`
   - on re-parse, write a new versioned output and refresh only this statement's status entry
5. Update only this input's status:
   - set `ready` when no trustworthy parsed evidence exists yet or manual follow-up is required before parsing is trustworthy
   - set `parsed` when normalized output is written and no warnings require `$auto-bean-import` review
   - set `parsed_with_warning` when normalized output is written but warnings need `$auto-bean-import` review before account inspection
   - never set `account_inspection`, `ready_for_categorization`, `ready_for_review`, `ready_to_write`, `final_review`, or `done`
   - record output path, parse run id, parser identifier, timestamps, warnings, blocking issues, and retry metadata alongside the status
   - when setting `ready`, increment `process_attempts` for the current source fingerprint, set `last_process_failure_reason`, and set `manual_resolution_required: true` once the current-fingerprint attempt count reaches 2
   - when the source fingerprint changes, start a new retry count for that fingerprint while preserving any prior failure context that remains useful in warnings or blocking issues
6. Continue through safe raw-to-parsed work while collecting questions:
   - follow the shared question-handling contract
   - keep progressing through every deterministic parsing, normalization, status, and evidence-quality step that does not require guessing
   - write one deterministic process artifact under `.auto-bean/artifacts/process/`, using the shared raw-statement artifact prefix from `$auto-bean-import`, such as `.auto-bean/artifacts/process/<artifact_prefix>--process.md`
   - use that process artifact for process-stage questions, manual extraction notes, source-memory reuse attribution, and processing-related `memory_suggestions`
   - reflect the process artifact path in the parsed output or status entry; do not embed long question payloads in the final response when the artifact can carry them
   - make unresolved items visible by recording explicit warnings or blocking issues in parsed/status artifacts
   - return the process artifact to `$auto-bean-import` so the orchestrator can ask and update or resume the intermediate statement
   - collect eligible reusable learning as `memory_suggestions` while working; include memory type, source context, decision, scope, confidence or review state, supporting evidence, current-evidence checks, and why it should be reused later
   - write every processing-related memory candidate into a `Memory Suggestions` section of the process artifact, even when there are no user questions
   - keep memory candidates in the returned `memory_suggestions` structure as well; do not create a separate temporary memory-suggestions artifact
7. Return control to `$auto-bean-import` with:
   - assigned source path and source fingerprint
   - parsed output path and parse run id
   - status change for this input
   - warnings, blockers, retry metadata, and evidence-quality result
   - memory reuse attribution if governed memory influenced parsing or source handling
   - every process artifact written under `.auto-bean/artifacts/process/`, with a short summary of the exact question/reason, affected intermediate-statement fields, source-memory attribution, and processing-related memory suggestions
   - `memory_suggestions`: every eligible reusable-learning candidate, or `[]` when none were found

Guardrails:

- Do not derive first-seen accounts, mutate account-opening structure, create transaction postings, reconciliation findings, commit requests, push requests, or final approval prompts.
- Do not write `.auto-bean/memory/**`; report possible reusable learning back to `$auto-bean-import` so it can decide whether to invoke `$auto-bean-memory`.
- Do not overwrite prior parse outputs silently unless `$auto-bean-import` explicitly assigned overwrite behavior.
- Do not claim success when evidence is ambiguous, structure is risky, or validation fails.
- Do not process unassigned statements.
- Do not ask for user input; follow the shared question-handling contract and make unresolved requirements visible in the relevant artifacts for `$auto-bean-import`.
