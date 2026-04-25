---
name: auto-bean-import
description: Orchestrate statement imports from raw statement discovery through delegated processing, delegated apply work, user-input surfacing, validation review, and final summary. Use when the user asks to import statements, process new raw statements, run the import workflow, or continue work from `statements/raw/` and `statements/import-status.yml`.
---

Use this as the user-facing import entrypoint. Delegate mechanics to narrower skills instead of duplicating their procedures.

Workflow:

1. Discover unprocessed work:
   - inspect `statements/raw/`, `statements/parsed/`, and `statements/import-status.yml`
   - fingerprint supported raw files: `.pdf`, `.csv`, `.xlsx`, `.xls`
   - select files with no current parsed output, missing status, changed fingerprint, `ready` status, or explicit user reprocess request
   - skip files already current at `parsed`, `parsed_with_warnings`, `in_review`, or `done`
2. Use sub-agents for statement work:
   - assign each sub-agent one raw statement
   - give each sub-agent the source path, current status entry, expected parsed-output path or naming rule, and the instruction to use `$auto-bean-process`
   - require sub-agents to persist all safe progress without asking the user directly, and to report parsed output paths, status changes, warnings, blockers, process question artifacts under `.auto-bean/artifacts/process/`, `memory_suggestions`, and `memory_suggestion_files`
   - wait for all assigned processing sub-agents to finish before starting any parsed-statement handoff
3. Resolve process questions and update intermediate statements:
   - inspect every reported process question artifact under `.auto-bean/artifacts/process/`
   - ask the user any bounded questions needed to make the parsed intermediate statement trustworthy before downstream work
   - include the affected statement path, observed facts, why input is needed, and the smallest useful set of choices or requested facts
   - after the user answers, update the relevant intermediate parsed statement, status entry, and process artifact when the answer resolves or changes parsed evidence
   - resume `$auto-bean-process` only when the answer requires parser-specific regeneration or normalization that should stay inside the raw-to-parsed worker boundary
   - keep statements that still have unresolved process questions out of first-seen derivation and posting work
4. Derive first-seen accounts:
   - for each parsed statement with resolved process questions and status `parsed` or `parsed_with_warnings`, inspect `beancount/accounts.beancount` first, then `ledger.beancount` and included `beancount/**` files for existing `open` directives and account names
   - classify inferred accounts as `existing_account`, `first_seen_candidate`, or `blocked_inference`
   - consider only banking, credit card, loans, cash, and investment account types for first-seen structure inference
   - do not infer mutable categories such as expense accounts
   - infer Beancount-safe account names and minimal supporting directives only when institution, account identity, type hints, and currency provide strong evidence
   - current parsed statement evidence and current ledger state remain authoritative; memory may provide hints, not authority
   - when top-level branch, account identity, currency, duplicate risk, mutation target, or syntax is unclear, ask the user a bounded question before mutating account structure
   - mutate only account-opening structure and minimal supporting directives such as missing operating currencies; prefer `beancount/accounts.beancount` and explain any fallback target
   - avoid duplicate directives and keep mutations deterministic for the same parsed input and ledger state
   - run `./scripts/validate-ledger.sh` or `./.venv/bin/bean-check ledger.beancount` after account-structure edits
   - keep statements with unresolved first-seen account questions out of posting work until resolved
5. Handoff parsed statements:
   - for each statement successfully processed to `parsed` or `parsed_with_warnings` with resolved process and first-seen account questions, start one sub-agent assigned to that single parsed statement with the instruction to use `$auto-bean-apply` for posting/reconciliation work
   - run apply sub-agents sequentially: wait for the current `$auto-bean-apply` sub-agent to finish before starting the next one
   - require each `$auto-bean-apply` sub-agent to persist all safe progress before asking for user input, and to report ledger edits, status changes, reconciliation findings, validation results, blockers, persisted pending user questions, `memory_suggestions`, and `memory_suggestion_files`
   - keep statements that need clarification, repair, or manual source handling out of final approval until resolved
6. Surface apply user input:
   - when any sub-agent or downstream skill reports missing information, risky ambiguity, unresolved reconciliation finding, or manual extraction need, first verify the relevant artifact/status/file records all safe progress and clearly names what remains required from the user
   - ask the user the collected bounded question or question set and wait for the answer instead of treating the workflow as finished or blocked
   - use the appropriate user-input tool or conversation channel; do not force clarification through a specific skill unless that skill owns the work being clarified
   - include the affected statement path, why input is needed, and the smallest useful set of choices or requested facts
   - after the user answers, resume the same first-seen derivation or apply stage for the affected statement/artifact with the answer and existing persisted artifacts included in the assignment context
7. Review and close:
   - consolidate sub-agent results, process question outcomes, first-seen account derivation, downstream apply results, validation outcome, and `git diff`
   - keep parsed facts, first-seen account edits, ledger postings, warnings, blockers, and required user decisions separate
   - do not mark entries `done` until the user approves the final import result
8. Collect and govern memory suggestions at the end:
   - collect `memory_suggestions` returned by every `$auto-bean-process` and `$auto-bean-apply` sub-agent, including resumed stages after user answers
   - read any returned `memory_suggestion_files` only when the path stays under `.auto-bean/tmp/memory-suggestions/`
   - before final response, look for memory suggestion files created during this import under `.auto-bean/tmp/memory-suggestions/`, include eligible files not already reported by sub-agents, and ignore unrelated files with a warning
   - ignore missing, invalid, path-unsafe, or unrelated suggestion files and report them as warnings
   - deduplicate suggestions that describe the same memory type, source, decision, and scope
   - keep raw statements, parsed statement dumps, ledger entries, diagnostics, and proposal artifacts out of the memory handoff
   - if no eligible suggestions remain, record that no governed memory persistence was requested
   - if eligible suggestions remain, invoke `$auto-bean-memory` with the collected suggestions, source/audit context, and explicit instruction to validate eligibility and persist only approved reusable operational learning through the governed workflow
   - report the `$auto-bean-memory` result separately from import parsing, posting, validation, and final approval status
   - include memory suggestions collected, ignored, deduplicated, handed to `$auto-bean-memory`, and persisted by `$auto-bean-memory`
   - do not write `.auto-bean/memory/**` directly

End with:

- processed, skipped, blocked, and user-input-needed statements
- parsed outputs written or reused
- first-seen account edits, ledger posting edits, and status changes
- validation result and remaining decisions
- memory suggestions collected and `$auto-bean-memory` persistence result, if any
- whether the import is ready for final approval, commit, or push

Guardrails:

- Keep raw files in `statements/raw/`, parsed evidence in `statements/parsed/`, status in `statements/import-status.yml`, and governed memory in `.auto-bean/memory/`.
- Keep `$auto-bean-process` responsible only for raw-to-parsed processing, process question artifacts, and process-stage memory suggestions.
- Keep `$auto-bean-import` responsible for process question surfacing, intermediate-statement updates, first-seen account derivation, and the final governed memory handoff.
- Keep `$auto-bean-apply` responsible for postings, reconciliation, validation review, and `in_review` status.
- Do not silently reprocess current statements.
