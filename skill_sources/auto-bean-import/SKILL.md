---
name: auto-bean-import
description: Normalize raw statement files into inspectable parsed outputs through the local Docling CLI, then create bounded first-seen ledger account structure directly from those parsed statements when the evidence is strong enough. Use when Codex needs to discover new statement files in `statements/raw/`, re-parse a specific statement, update `statements/import-status.yml`, preserve outputs under `statements/parsed/`, inspect current ledger structure, write direct account-opening mutations under `beancount/**` or `ledger.beancount`, run validation, present a single post-mutation review surface, show a git-backed diff, and ask whether to commit or push the result.
---

Read these references before acting:

- `.agents/skills/auto-bean-import/references/parsed-statement-output.example.json`
- `.agents/skills/auto-bean-import/references/import-status.example.yml`

Read this additional reference only when deeper diagnostic review is warranted:

- `.agents/skills/auto-bean-import/references/account-proposal.example.json`

Load `.agents/skills/shared/mutation-pipeline.md` and `.agents/skills/shared/mutation-authority-matrix.md` before mutating ledger structure.

Follow this workflow:

1. Confirm the request in workspace terms:
   - discover new or stale raw statements under `statements/raw/`, or
   - re-parse one specific statement path or filename.
   - if parsed statements already exist, clarify whether the user wants parse-only results or the full direct import-to-ledger account-structure workflow
2. Preserve trust boundaries:
   - do not write durable memory under `.auto-bean/memory/**`
   - do not create transaction postings, reconciliation decisions, or accepted categorization memory
   - keep raw inputs in `statements/raw/`, parsed outputs in `statements/parsed/`, parse state in `statements/import-status.yml`, and optional governed diagnostics under `.auto-bean/proposals/` or `.auto-bean/artifacts/` only when review depth or troubleshooting justifies persistence
   - treat `statements/parsed/*.json` and `statements/import-status.yml` as intake evidence, not as accepted ledger changes
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
8. Derive direct account-structure edits only from normalized parsed outputs and current ledger state:
   - inspect the relevant `statements/parsed/*.json` outputs before inferring structure; do not re-parse raw statements just to infer accounts
   - inspect `beancount/accounts.beancount` first when it exists, because that is the preferred workspace location for durable account `open` directives
   - then inspect `ledger.beancount` and any other included `beancount/**` files to find existing `open` directives, existing `option "operating_currency"` declarations, and the current baseline structure
   - treat account-level evidence as a combination of institution name, masked account number, statement title, account type hints, statement currency, and any explicit labels in the parsed records
   - classify each inferred account as exactly one of: `existing_account`, `first_seen_candidate`, or `blocked_inference`
   - fail closed when the evidence does not support a stable top-level Beancount branch such as `Assets` or `Liabilities`
   - infer Beancount-safe account names, optional currency constraints, and minimal supporting directives only when the parsed evidence supports them
   - prefer adding new account-opening structure in `beancount/accounts.beancount`; if the workspace does not yet have that file, explain the fallback path before mutating another target
   - add `option "operating_currency" "XYZ"` only when the imported evidence introduces a currency the ledger does not already declare
   - add `Equity:Opening-Balances` support only when the ledger baseline or imported account path actually needs it and avoid duplicating an existing directive
   - when the workspace still uses the minimal generated baseline ledger, enrich that baseline from imported evidence instead of sending the user to manual account setup
   - when related account structure already exists, write only the missing additions and explain why duplicates were skipped
9. Apply direct ledger mutations safely and keep them bounded:
   - mutate only account-opening structure and minimal supporting directives needed for that structure
   - do not create transaction postings, transfer detection, duplicate handling, reconciliation outcomes, or durable memory writes in this workflow
   - preserve the current workspace layout and mutate the smallest viable set of files
   - keep the mutation deterministic for the same parsed inputs and ledger state
10. Validate immediately after mutation:
   - run the standard ledger validation gate after direct mutation and never present a failed validation result as success
   - if validation fails, stop before any finalization claim, keep the working-tree change unfinalized, and preserve enough local audit context under `.auto-bean/artifacts/` for inspection and troubleshooting
11. Present inspectable change context before any finalization:
   - present a single post-mutation review surface before any commit/push request
   - separate parsed statement facts from derived ledger edits so the user can see which normalized records came from statement parsing versus which `ledger.beancount` or `beancount/**` changes were inferred from those records
   - summarize which files changed
   - summarize what account structure was inferred and why that inference was made from the imported statement evidence
   - include the validation outcome, warnings, blocked inferences, low-confidence edits, and any ambiguous results directly in that review package
   - state explicitly that commit/push remains the final approval boundary even when the working tree has already changed
   - show a git-backed diff for the changed files
   - ask whether the agent should commit and push only after the mutation and validation result are available
12. Fail closed for ambiguity or risky structure:
   - block finalization when the evidence does not support a stable top-level Beancount branch or otherwise leaves the structural inference unclear
   - block finalization when the mutation target is unclear, duplicate-sensitive, or would extend the ledger beyond bounded account structure
   - let the user stop, defer, or reject finalization without corrupting prior accepted ledger history
   - when finalization is blocked, deferred, or rejected, record narrow local audit context under `.auto-bean/artifacts/` when durable troubleshooting evidence will help later inspection
   - create `.auto-bean/proposals/` diagnostics only when the user asks for deeper review or when the change is risky enough that a durable diagnostic artifact will help inspection
13. Use parallel workers only when platform policy permits and the user explicitly asks for parallelism or bounded delegation:
   - assign each worker one raw statement by default
   - use a small batch only when the file count is higher than the practical worker cap
   - require each worker to return a structured result with source path, parse status, normalized output path, warnings, and blocking issues
   - if workers also contribute account evidence, require them to return only bounded evidence summaries; final account classification, mutation, validation, and diff review stay with the parent agent
   - keep each worker bounded to its assigned source file and parse-output target
   - consolidate all worker results in the parent summary and fail closed for any worker that times out, errors, or needs approval that cannot be surfaced
14. End with a concise import summary:
   - which statements were processed
   - which were skipped and why
   - which outputs were written under `statements/parsed/`
   - which parsed statement facts were reviewed before any ledger acceptance decision
   - which account mutations were applied, skipped, or blocked
   - which derived ledger edits remain unfinalized pending user approval
   - whether validation passed
   - whether the result is ready for commit/push approval
   - whether the user chose to stop, defer, or reject finalization
   - any blocked or failed statements or ambiguous inferences that still need user attention

Guardrails:

- Keep all contract keys in `snake_case`.
- Keep parsed-statement artifacts narrow: extracted statement facts and diagnostics only.
- Keep optional proposal artifacts narrow: diagnostic review context only, not the default success path.
- Do not overwrite prior parse outputs silently unless the user explicitly asks for overwrite behavior.
- Do not claim the import succeeded when evidence is ambiguous, structurally risky, or validation fails.
- Do not create a second approval system beyond validation plus explicit commit/push approval.
- Keep the review package deterministic, concise, and stage-based so long-running CLI work stays inspectable.
- Prefer local shell tools and the workspace runtime over adding new product Python modules.
