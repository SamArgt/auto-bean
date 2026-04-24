---
name: auto-bean-import
description: Normalize raw statement files into inspectable parsed outputs through the local Docling CLI, then create bounded first-seen ledger account structure directly from those parsed statements when the evidence is strong enough.
---

Read these references before acting:

- `.agents/skills/shared/beancount-syntax-and-best-practices.md` when inferring Beancount account names, `open` directives, currency constraints, or other ledger syntax
- `.agents/skills/shared/memory-access-rules.md` before reading governed memory as advisory import context or when a finalized import result reveals reusable memory
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
   - governed memory is advisory only and comes from `.auto-bean/memory/`
   - do not create postings, reconciliation outcomes, categorization memory, or open-ended preference memory here
3. Plan from current state:
   - read `statements/import-status.yml`
   - scan `statements/raw/` for `.pdf`, `.csv`, `.xlsx`, `.xls`
   - compute a deterministic fingerprint such as `sha256`
   - Read `.auto-bean/memory/import_sources/index.json` first when looking for reusable import-source behavior.
   - Only read `.auto-bean/memory/import_sources/<source_slug>.json` when an index entry matches current source identity, institution, account hints, statement shape, or source fingerprint.
   - Treat matched source memory as advisory guidance for parsing, source handling, and account-structure hints; fail closed if memory is missing, malformed, too broad, stale, or conflicts with current evidence.
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
   - current parsed statement evidence and current ledger state remain authoritative; memory may supply hints, not authority, for source-specific naming or account-structure suggestions.
   - fail closed when the top-level branch, mutation target, or duplicate risk is unclear
8. Use `auto-bean-query` when import needs ledger analysis instead of structure inspection:
   - hand off to `$auto-bean-query` before answering questions about balances, historical account activity, date-bounded totals, register rows, transaction existence, or whether imported evidence matches already-posted ledger activity.
   - do not approximate those answers by manually grepping ledger entries when `bean-query` can answer them.
   - keep direct file inspection for `open` directives, account hierarchy, include structure, and syntax needed to make bounded first-seen account-opening changes.
   - query the root ledger, normally `ledger.beancount`, with the narrowest useful `bean-query ledger.beancount 'SELECT ...'` command.
   - use explicit account names, account patterns, and date windows; start with grouped summaries, then drill into register-style detail only when needed.
   - treat `position` and `balance` as inventories that may contain multiple commodities or lots; use `units(sum(position))` or `cost(sum(position))` when that distinction matters.
   - use `FROM OPEN ON ... CLOSE ON ...` for reporting windows, and explain that semantic choice in the review surface when it affects the result.
   - if a query result is empty, treat it as ambiguous until checked against account-name, date-window, and pattern assumptions.
9. Apply only bounded ledger mutations:
   - mutate only account-opening structure and minimal supporting directives such as missing operating currencies
   - prefer `beancount/accounts.beancount`; explain any fallback target before mutating it
   - avoid duplicate directives and keep the mutation deterministic for the same parsed inputs and ledger state
10. Validate immediately after any ledger mutation:
   - run `./scripts/validate-ledger.sh` or `./.venv/bin/bean-check ledger.beancount`
   - if validation fails, stop before any success claim and preserve local audit context
11. Present one review surface before finalization:
   - separate parsed statement facts from inferred ledger edits
   - include any `$auto-bean-query` command, final BQL query, result caveats, and interpretation when ledger analysis was required
   - include a `Memory reuse attribution` section whenever governed memory influenced parsing, source handling, or account-structure suggestions. For each influence, list memory path, `memory_type`, record identity or stable summary, matched current evidence, decision influenced, and limits on reuse.
   - summarize changed files, inferred accounts, warnings, blocked inferences, and validation outcome
   - show a git-backed diff for changed files
   - state that commit/push remains the final approval boundary
   - suggest an `$auto-bean-memory` persistence request only after a trustworthy finalized outcome; let the orchestrator decide whether to invoke the governed memory workflow
12. Handoff postings to `auto-bean-apply`:
   - use `statements/parsed/*.json` and `statements/import-status.yml` as the evidence handoff
   - only hand off statements whose status is `parsed` or `parsed_with_warnings`
   - do not generate or apply transaction postings inside `auto-bean-import`
13. End with a concise import summary:
   - processed and skipped statements
   - outputs written under `statements/parsed/`
   - account mutations applied, skipped, or blocked
   - whether validation passed
   - whether the result is ready for commit/push approval
   - any suggested governed memory updates
   - any blocked or failed statements that still need attention

Guardrails:

- Keep all contract keys in `snake_case`.
- Keep source context narrow: source identity, statement-shape hints, account-structure reuse hints, parse or mapping guidance, review metadata, and timestamps only.
- Do not write `.auto-bean/memory/**` directly; hand eligible approved learning to `$auto-bean-memory`.
- Do not overwrite prior parse outputs silently unless the user explicitly asks for overwrite behavior.
- Do not claim success when evidence is ambiguous, structure is risky, or validation fails.
- Do not introduce a second approval system beyond validation plus explicit commit/push approval.
- Keep the review package deterministic, concise, and stage-based.
