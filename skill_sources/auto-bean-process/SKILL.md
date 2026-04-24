---
name: auto-bean-process
description: Process exactly one assigned raw statement file into normalized parsed evidence and optional first-seen account structure through the local Docling CLI. Use only as an internal worker stage for `$auto-bean-import`; do not discover import work, invoke posting workflows, or orchestrate finalization.
---

Use this only for the raw-to-parsed stage assigned by `$auto-bean-import`.

Inputs from `$auto-bean-import`:

- one raw statement path under `statements/raw/`
- the matching `statements/import-status.yml` entry when one exists
- the expected parsed-output path or naming rule
- any relevant source-memory hint already selected for this input

Read before acting:

- `.agents/skills/shared/beancount-syntax-and-best-practices.md` when inferring Beancount account names, `open` directives, currency constraints, or other ledger syntax
- `.agents/skills/shared/memory-access-rules.md` before using governed memory hints
- `.agents/skills/auto-bean-process/references/parsed-statement-output.example.json`
- `.agents/skills/auto-bean-process/references/import-status.example.yml`

Workflow:

1. Confirm the assigned scope:
   - process only the assigned raw statement path
   - do not scan `statements/raw/` for more work
   - do not invoke `$auto-bean-apply`
   - keep raw inputs in `statements/raw/`, parsed outputs in `statements/parsed/`, and parse state in `statements/import-status.yml`
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
   - set `parsed` when normalized output is written and no warnings block posting work
   - set `parsed_with_warnings` when normalized output is written but warnings need review before posting work
   - never set `in_review` or `done`
   - record output path, parse run id, parser identifier, timestamps, warnings, and blocking issues alongside the status
6. Derive first-seen account structure only from this normalized output plus current ledger state:
   - inspect `beancount/accounts.beancount` first, then `ledger.beancount` and included `beancount/**` files for existing `open` directives and account names
   - classify inferred accounts as `existing_account`, `first_seen_candidate`, or `blocked_inference`
   - consider only banking, credit card, loans, cash, and investment account types for first-seen structure inference
   - do not infer mutable categories such as expense accounts
   - infer Beancount-safe account names and minimal supporting directives only when institution, account identity, type hints, and currency provide strong evidence
   - current parsed statement evidence and current ledger state remain authoritative; memory may provide hints, not authority
   - fail closed when top-level branch, account identity, currency, duplicate risk, mutation target, or syntax is unclear
7. Apply only bounded account-structure mutations:
   - mutate only account-opening structure and minimal supporting directives such as missing operating currencies
   - prefer `beancount/accounts.beancount`; explain any fallback target in the worker result
   - avoid duplicate directives and keep mutation deterministic for the same parsed input and ledger state
8. Validate only mutations made by this stage:
   - run `./scripts/validate-ledger.sh` or `./.venv/bin/bean-check ledger.beancount` after account-structure edits
   - if validation fails, stop before any success claim and report the failure as a blocker
9. Return control to `$auto-bean-import` with:
   - assigned source path and source fingerprint
   - parsed output path and parse run id
   - status change for this input
   - account classification and account-structure edits, if any
   - warnings, blockers, and validation result
   - memory reuse attribution if governed memory influenced parsing, source handling, or account-structure hints
   - whether user input is required, with the exact question/reason
   - possible reusable learning, without writing memory

Guardrails:

- Do not create transaction postings, reconciliation findings, commit requests, push requests, or final approval prompts.
- Do not write `.auto-bean/memory/**`; report possible reusable learning back to `$auto-bean-import` so it can decide whether to invoke `$auto-bean-memory`.
- Do not overwrite prior parse outputs silently unless `$auto-bean-import` explicitly assigned overwrite behavior.
- Do not claim success when evidence is ambiguous, structure is risky, or validation fails.
- Do not process unassigned statements.
