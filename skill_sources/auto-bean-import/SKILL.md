---
name: auto-bean-import
description: Normalize raw statement files into inspectable parsed outputs through the local Docling CLI, then create bounded first-seen ledger account structure directly from those parsed statements when the evidence is strong enough.
---

Read these references before acting:

- `.agents/skills/shared/beancount-syntax-and-best-practices.md` when inferring Beancount account names, `open` directives, currency constraints, or other ledger syntax
- `.agents/skills/auto-bean-import/references/parsed-statement-output.example.json`
- `.agents/skills/auto-bean-import/references/import-status.example.yml`

Follow this workflow:

1. Confirm scope in workspace terms:
   - discover new or stale files in `statements/raw/`, or
   - re-parse a specific file.
   - if parsed outputs already exist, distinguish parse-only, account-structure import, or handoff to `auto-bean-apply` for postings.
2. Preserve boundaries:
   - raw inputs stay in `statements/raw/`
   - normalized outputs stay in `statements/parsed/`
   - parse state stays in `statements/import-status.yml`
   - use only these workflow statuses in `statements/import-status.yml`:
     - `ready`: no actions have been taken yet; ready for import
     - `parsed`: parsed and written under `statements/parsed/`, but no transactions have been posted to the workspace
     - `parsed_with_warnings`: parsed and written under `statements/parsed/`, but warnings still need review before transactions are ready to post
     - `in_review`: import-derived transactions have been written in the workspace, but the result has not been validated and finalized yet
     - `done`: the full import/apply workflow is complete
   - source-context memory is advisory only and comes from `.auto-bean/memory/import_sources/`
   - do not create postings, reconciliation outcomes, categorization memory, or open-ended preference memory here
3. Plan from current state:
   - read `statements/import-status.yml`
   - scan `statements/raw/` for `.pdf`, `.csv`, `.xlsx`, `.xls`
   - compute a deterministic fingerprint such as `sha256`
   - scan the first 30 lines of `.auto-bean/memory/import_sources/` for any relevant source-context hints that match the current source identity, statement shape, or account structure. If it matches, read the whole file and keep it in mind as advisory guidance but not authority. Do not skip current-evidence checks, validation, or approval just because of memory hints.
4. Parse with the local Docling CLI:
   - call `./.venv/bin/docling` directly on the assigned source
   - request JSON output into a unique temp path under `.auto-bean/tmp/`
   - default CLI patterns:
     - PDF: `./.venv/bin/docling statements/raw/bank/jan-2026.pdf --to json --output .auto-bean/tmp/docling-20260411T090000Z-jan-2026-1ef7e13f`
     - CSV: `./.venv/bin/docling statements/raw/cards/2026-01.csv --to json --output .auto-bean/tmp/docling-20260411T090000Z-2026-01-csv-a82c91d4`
     - Excel: `./.venv/bin/docling statements/raw/brokerage/holdings-2026-01.xlsx --to json --output .auto-bean/tmp/docling-20260411T090000Z-holdings-2026-01-6cb2e40a`
     - bounded batch: `./.venv/bin/docling ./worker-input --from pdf --from csv --from xlsx --to json --output .auto-bean/tmp/docling-batch-worker-02-20260411T090000Z`
   - translate Docling output into the normalized contract from the references
   - delete temp artifacts after the normalized output is safely written unless active debugging needs them
   - if unsure about Docling CLI flags, supported formats, or dependency behavior, use Context7 to check the relevant docs before adapting the command
   - if Docling or a required local dependency is missing, report the concrete failure and stop for that file
   - if a scanned or textless PDF cannot be extracted, do not guess; leave the statement at `ready` and record the issue clearly for follow-up
5. Persist normalized outputs:
   - write one deterministic JSON artifact per source or parse run under `statements/parsed/`
   - include `parse_run_id`, `source_fingerprint`, parser details, `status`, warnings, blocking issues, and extracted records
   - on re-parse, write a new versioned output and refresh the same statement entry in `statements/import-status.yml`
6. Keep `statements/import-status.yml` in sync after every attempt:
   - set `status: ready` before any import work has succeeded yet, and also when an attempted parse still needs manual follow-up before trustworthy parsed evidence exists
   - set `status: parsed` when the normalized output is written and there are no warnings blocking posting work
   - set `status: parsed_with_warnings` when the normalized output is written but warnings still need review before posting work
   - never set `status: in_review` or `status: done` during `auto-bean-import`; those belong to the posting/finalization stage
   - record output path, parse run id, parser identifier, timestamps, warnings, and blocking issues alongside the status
7. Derive first seen account structure only from normalized outputs plus current ledger state:
   - inspect `statements/parsed/*.json` before inferring structure
   - inspect `beancount/accounts.beancount` first, then `ledger.beancount` and included `beancount/**` files for `open` directives and existing account names.
   - classify each inferred account as `existing_account`, `first_seen_candidate`, or `blocked_inference`
   - consider only banking, credit card, loans, cash, and investment account types for first-seen structure inference; do not infer structure for expenses account types or others that are more mutable and less likely to have strong identity evidence.
   - infer Beancount-safe account names and minimal supporting directives only when institution, account identity, type hints, and currency provide strong evidence
   - fail closed when the top-level branch, mutation target, or duplicate risk is unclear
8. Apply only bounded ledger mutations:
   - mutate only account-opening structure and minimal supporting directives such as missing operating currencies
   - prefer `beancount/accounts.beancount`; explain any fallback target before mutating it
   - avoid duplicate directives and keep the mutation deterministic for the same parsed inputs and ledger state
9. Validate immediately after any ledger mutation:
   - run `./scripts/validate-ledger.sh` or `./.venv/bin/bean-check ledger.beancount`
   - if validation fails, stop before any success claim and preserve local audit context
10. Present one review surface before finalization:
   - separate parsed statement facts from inferred ledger edits
   - summarize changed files, inferred accounts, warnings, blocked inferences, and validation outcome
   - show a git-backed diff for changed files
   - state that commit/push remains the final approval boundary
   - suggest source-context create or update only after a trustworthy finalized outcome; let the orchestrator decide whether to write it
11. Handoff postings to `auto-bean-apply`:
   - use `statements/parsed/*.json` and `statements/import-status.yml` as the evidence handoff
   - only hand off statements whose status is `parsed` or `parsed_with_warnings`
   - do not generate or apply transaction postings inside `auto-bean-import`
12. End with a concise import summary:
   - processed and skipped statements
   - outputs written under `statements/parsed/`
   - account mutations applied, skipped, or blocked
   - whether validation passed
   - whether the result is ready for commit/push approval
   - any suggested source-context updates
   - any blocked or failed statements that still need attention

Guardrails:

- Keep all contract keys in `snake_case`.
- Keep source context narrow: source identity, statement-shape hints, account-structure reuse hints, parse or mapping guidance, review metadata, and timestamps only.
- Do not overwrite prior parse outputs silently unless the user explicitly asks for overwrite behavior.
- Do not claim success when evidence is ambiguous, structure is risky, or validation fails.
- Do not introduce a second approval system beyond validation plus explicit commit/push approval.
- Keep the review package deterministic, concise, and stage-based.
