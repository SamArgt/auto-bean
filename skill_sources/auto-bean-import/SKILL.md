---
name: auto-bean-import
description: Normalize raw statement files into inspectable parsed outputs through the local Docling CLI, then derive reviewable first-seen account proposals from those parsed statements without mutating the ledger. Use when Codex needs to discover new statement files in `statements/raw/`, re-parse a specific statement, update `statements/import-status.yml`, preserve outputs under `statements/parsed/`, propose import-derived account structure, and keep ledger and memory files untouched until explicit review succeeds.
---

Read these references before acting:

- `.agents/skills/auto-bean-import/references/parsed-statement-output.example.json`
- `.agents/skills/auto-bean-import/references/import-status.example.yml`
- `.agents/skills/auto-bean-import/references/account-proposal.example.json`

Follow this workflow:

1. Confirm the request in workspace terms:
   - discover new or stale raw statements under `statements/raw/`, or
   - re-parse one specific statement path or filename.
   - if parsed statements already exist, clarify whether the user wants parse-only results or also wants first-seen account proposals from the parsed evidence
2. Preserve trust boundaries:
   - do not mutate `ledger.beancount` or `beancount/**`
   - do not write durable memory under `.auto-bean/memory/**`
   - do not create transaction postings, reconciliation decisions, or accepted mutation plans
   - keep raw inputs in `statements/raw/`, parsed outputs in `statements/parsed/`, parse state in `statements/import-status.yml`, and governed proposal artifacts under `.auto-bean/proposals/` when review depth justifies persistence
3. Load and compare parse state before choosing work:
   - read `statements/import-status.yml` first
   - scan `statements/raw/` for supported inputs: `.pdf`, `.csv`, `.xlsx`, `.xls`
   - compute a deterministic source fingerprint such as `sha256`
   - in discover mode, parse only files that are new, stale, failed, blocked, or explicitly requested
   - in targeted re-parse mode, process only the requested statement and leave unrelated files untouched
4. Invoke Docling through the local CLI instead of writing bespoke parsers:
   - use the assigned raw statement path as the only input
   - call `./.venv/bin/docling` directly instead of doing a separate readiness preflight
   - request JSON output and write Docling's raw output to a temporary staging location first
   - make the staging directory or filename unique per source file and parse run so parallel workers do not collide; include values such as `parse_run_id`, a short source slug, and a short fingerprint fragment
   - translate the Docling result into the normalized contract from the reference file
   - remove the staged Docling JSON file and any worker-specific temp directory after the normalized `statements/parsed/` artifact is safely written, or after a failed run when the temp files are no longer needed for debugging
   - if the Docling command fails because the CLI or a required local dependency is missing, report that concrete failure and stop for that file instead of masking it behind an extra readiness check
   - if the source is a scanned or textless PDF and Docling cannot extract usable text, record a structured `blocked` result instead of guessing
5. Use these CLI patterns as the default starting point and adapt only when the source format or Docling version requires it:
   - single-file PDF to staged JSON:
     - `./.venv/bin/docling statements/raw/bank/jan-2026.pdf --to json --output .auto-bean/tmp/docling-20260411T090000Z-jan-2026-1ef7e13f`
   - single-file CSV to staged JSON:
     - `./.venv/bin/docling statements/raw/cards/2026-01.csv --to json --output .auto-bean/tmp/docling-20260411T090000Z-2026-01-csv-a82c91d4`
   - single-file Excel to staged JSON:
     - `./.venv/bin/docling statements/raw/brokerage/holdings-2026-01.xlsx --to json --output .auto-bean/tmp/docling-20260411T090000Z-holdings-2026-01-6cb2e40a`
   - bounded batch for a worker assigned multiple files:
     - `./.venv/bin/docling ./worker-input --from pdf --from csv --from xlsx --to json --output .auto-bean/tmp/docling-batch-worker-02-20260411T090000Z`
   - after Docling writes its JSON output, translate that staged file into the normalized `statements/parsed/` contract rather than exposing raw Docling output as the final artifact
   - once the normalized artifact is committed to `statements/parsed/`, delete the staged Docling JSON and temp directory unless you intentionally need to retain them for an active debugging handoff
6. Persist normalized outputs under `statements/parsed/`:
   - write one JSON output per source file or parse run using deterministic, source-preserving names
   - keep paths workspace-relative where practical
   - include `parse_run_id`, `source_fingerprint`, parser details, warnings, blocking issues, and extracted records
   - preserve prior parse context on re-parse by writing a new versioned output and marking the new output as superseding the previous run when applicable
7. Keep `statements/import-status.yml` synchronized after every parse attempt:
   - update status for `parsed`, `parsed_with_warnings`, `blocked`, `failed`, `stale`, or `superseded`
   - record the latest parse output path, latest parse run id, parser identifier, timestamps, warnings, and blocking issues
   - do not infer durable status from conversation history alone
8. Derive first-seen account proposals only from normalized parsed outputs and current ledger state:
   - inspect the relevant `statements/parsed/*.json` outputs before proposing structure; do not re-parse raw statements just to infer accounts
   - inspect `beancount/accounts.beancount` first when it exists, because that is the preferred workspace location for durable account `open` directives
   - then inspect `ledger.beancount` and any other included `beancount/**` files to find existing `open` directives, existing `option "operating_currency"` declarations, and the current baseline structure
   - treat account-level evidence as a combination of institution name, masked account number, statement title, account type hints, statement currency, and any explicit labels in the parsed records
   - classify each inferred account as exactly one of: `existing_account`, `first_seen_candidate`, or `blocked_inference`
   - fail closed when the evidence does not support a stable top-level Beancount branch such as `Assets` or `Liabilities`
   - generate candidate `open` directives using Beancount-safe account names and add optional currency constraints only when the parsed evidence supports them
   - prefer proposing new account `open` directives in `beancount/accounts.beancount`; if the workspace does not yet have that file, explain the fallback path before proposing another target
   - propose `option "operating_currency" "XYZ"` only when the imported evidence introduces a currency the ledger does not already declare
   - propose `Equity:Opening-Balances` support only when the ledger baseline or imported account path actually needs it and avoid duplicating an existing directive
   - when the workspace still uses the minimal generated baseline ledger, propose enriching that baseline from imported evidence instead of sending the user to manual account setup
   - when related account structure already exists, propose only the missing additions and explain why duplicates were skipped
9. Write the proposal result as a narrow, reviewable artifact:
   - use the contract shape in `account-proposal.example.json` as the default
   - include source evidence links such as `parse_run_id`, `source_file`, `source_fingerprint`, statement labels, and confidence or issue notes
   - keep the artifact limited to account-structure planning: first-seen accounts, supporting directives, ambiguity notes, and review handoff metadata
   - do not include transaction postings, transfer detection, duplicate transaction handling, durable memory writes, or accepted ledger edits
   - keep proposal keys in `snake_case`
10. Route all structurally meaningful proposals through the existing review/apply boundary:
   - summarize what structure was inferred, why it was inferred from the imported statements, which ledger files would change, and what remains uncertain
   - hand off reviewable structural changes through `.agents/skills/auto-bean-apply/` and the shared mutation policy files
   - create a governed proposal artifact under `.auto-bean/proposals/` when the user asks for deeper inspection or the structural change is risky enough to justify durable review context
   - preserve any related diagnostics under `.auto-bean/artifacts/` when troubleshooting or review context would otherwise be lost
   - do not silently edit `ledger.beancount` or `beancount/**`, and do not describe the proposal as accepted until explicit approval and post-change validation both succeed
11. Use parallel workers only when platform policy permits and the user explicitly asks for parallelism or bounded delegation:
   - assign each worker one raw statement by default
   - use a small batch only when the file count is higher than the practical worker cap
   - require each worker to return a structured result with source path, parse status, normalized output path, warnings, and blocking issues
   - if workers also contribute account evidence, require them to return only bounded proposal inputs or draft proposal fragments; final proposal classification and review handoff stay with the parent agent
   - keep each worker bounded to its assigned source file and parse-output target
   - consolidate all worker results in the parent summary and fail closed for any worker that times out, errors, or needs approval that cannot be surfaced
12. End with a concise import summary:
   - which statements were processed
   - which were skipped and why
   - which outputs were written under `statements/parsed/`
   - which first-seen account proposals were produced, skipped, or blocked
   - whether the result is ready for `auto-bean-apply` review
   - any blocked or failed statements or ambiguous inferences that still need user attention

Guardrails:

- Keep all contract keys in `snake_case`.
- Keep parsed-statement artifacts narrow: extracted statement facts and diagnostics only.
- Keep account proposal artifacts narrow: account-structure planning and review handoff only.
- Do not overwrite prior parse outputs silently unless the user explicitly asks for overwrite behavior.
- Do not invent a second approval system when `auto-bean-apply` already covers the structural review boundary.
- Prefer local shell tools and the workspace runtime over adding new product Python modules.
