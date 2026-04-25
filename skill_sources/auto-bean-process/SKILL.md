---
name: auto-bean-process
description: Process exactly one assigned raw statement file into normalized parsed evidence through the local Docling CLI, recording process questions and memory suggestions for `$auto-bean-import`. Use only as an internal worker stage for `$auto-bean-import`; do not discover import work, derive first-seen accounts, invoke posting workflows, or orchestrate finalization.
---

Use this only for the raw-to-parsed stage assigned by `$auto-bean-import`.

Inputs from `$auto-bean-import`:

- one raw statement path under `statements/raw/`
- the matching `statements/import-status.yml` entry when one exists
- the expected parsed-output path or naming rule
- any relevant source-memory hint already selected for this input

Read before acting:

- `.agents/skills/shared/memory-access-rules.md` before using governed memory hints
- `.agents/skills/shared/parsed-statement-output.example.json`
- `.agents/skills/shared/parsed-statement-jq-reading.md` before inspecting large parsed statement artifacts
- `.agents/skills/shared/import-status.example.yml`

Workflow:

1. Confirm the assigned scope:
   - process only the assigned raw statement path
   - do not scan `statements/raw/` for more work
   - do not invoke `$auto-bean-categorize`
   - keep raw inputs in `statements/raw/`, parsed outputs in `statements/parsed/`, parse state in `statements/import-status.yml`, and process question artifacts in `.auto-bean/artifacts/process/`
2. Plan from this input:
   - verify the source exists and is `.pdf`, `.csv`, `.xlsx`, or `.xls`
   - compute a deterministic fingerprint such as `sha256`
   - compare the fingerprint to the supplied status entry, if any
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
   - set `parsed_with_warning` when normalized output is written but warnings need `$auto-bean-import` review before categorization
   - never set `ready_for_categorization`, `ready_for_review`, `ready_to_write`, `final_review`, or `done`
   - record output path, parse run id, parser identifier, timestamps, warnings, and blocking issues alongside the status
6. Continue through safe raw-to-parsed work while collecting questions:
   - do not stop at the first missing detail once parsed evidence can be written safely
   - keep progressing through every deterministic parsing, normalization, status, and evidence-quality step that does not require guessing
   - collect user questions in one deterministic artifact under `.auto-bean/artifacts/process/`, named from the parse run id or source fingerprint
   - each process question must include the affected source record or parsed-output path, observed facts, why guessing is unsafe, the answer needed to continue, and the intermediate-statement fields that may need revision after the answer
   - reflect the question artifact path in the parsed output or status entry; do not embed long question payloads in the final response when the artifact can carry them
   - make unresolved items visible by recording explicit warnings or blocking issues in parsed/status artifacts
   - do not ask the user directly; return the question artifact to `$auto-bean-import` so the orchestrator can ask and update or resume the intermediate statement
   - collect eligible reusable learning as `memory_suggestions` while working; include memory type, source context, decision, scope, confidence or review state, supporting evidence, current-evidence checks, and why it should be reused later
   - if the final response cannot carry all `memory_suggestions`, persist them in one JSON file under `.auto-bean/tmp/memory-suggestions/` named from the parse run id or source fingerprint, then return that path to `$auto-bean-import`
7. Return control to `$auto-bean-import` with:
   - assigned source path and source fingerprint
   - parsed output path and parse run id
   - status change for this input
   - warnings, blockers, and evidence-quality result
   - memory reuse attribution if governed memory influenced parsing or source handling
   - every process question artifact written under `.auto-bean/artifacts/process/`, with a short summary of the exact question/reason and affected intermediate-statement fields
   - `memory_suggestions`: every eligible reusable-learning candidate, or `[]` when none were found
   - `memory_suggestion_files`: any `.auto-bean/tmp/memory-suggestions/*.json` files created because suggestions were too large for the response

Guardrails:

- Do not derive first-seen accounts, mutate account-opening structure, create transaction postings, reconciliation findings, commit requests, push requests, or final approval prompts.
- Do not write `.auto-bean/memory/**`; report possible reusable learning back to `$auto-bean-import` so it can decide whether to invoke `$auto-bean-memory`.
- Do not overwrite prior parse outputs silently unless `$auto-bean-import` explicitly assigned overwrite behavior.
- Do not claim success when evidence is ambiguous, structure is risky, or validation fails.
- Do not process unassigned statements.
- Do not ask for user input; persist all safe progress and make unresolved requirements visible in the relevant artifacts for `$auto-bean-import`.
