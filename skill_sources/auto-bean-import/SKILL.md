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
   - require sub-agents to persist all safe progress before asking for user input, and to report parsed output paths, status changes, account-structure edits, warnings, blockers, persisted pending user questions, `memory_suggestions`, and `memory_suggestion_files`
   - wait for all assigned processing sub-agents to finish before starting any parsed-statement handoff
3. Handoff parsed statements:
   - for each statement successfully processed to `parsed` or `parsed_with_warnings`, start one sub-agent assigned to that single parsed statement with the instruction to use `$auto-bean-apply` for posting/reconciliation work
   - run apply sub-agents sequentially: wait for the current `$auto-bean-apply` sub-agent to finish before starting the next one
   - require each `$auto-bean-apply` sub-agent to persist all safe progress before asking for user input, and to report ledger edits, status changes, reconciliation findings, validation results, blockers, persisted pending user questions, `memory_suggestions`, and `memory_suggestion_files`
   - keep statements that need clarification, repair, or manual source handling out of final approval until resolved
4. Surface user input:
   - when any sub-agent or downstream skill reports missing information, risky ambiguity, unresolved reconciliation finding, or manual extraction need, first verify the relevant artifact/status/file records all safe progress and clearly names what remains required from the user
   - ask the user the collected bounded question or question set and wait for the answer instead of treating the workflow as finished or blocked
   - use the appropriate user-input tool or conversation channel; do not force clarification through a specific skill unless that skill owns the work being clarified
   - include the affected statement path, why input is needed, and the smallest useful set of choices or requested facts
   - after the user answers, resume the same processing or apply stage for the affected statement/artifact with the answer and existing persisted artifacts included in the assignment context
5. Collect and govern memory suggestions:
   - collect `memory_suggestions` returned by every `$auto-bean-process` and `$auto-bean-apply` sub-agent, including resumed stages after user answers
   - read any returned `memory_suggestion_files` only when the path stays under `.auto-bean/tmp/memory-suggestions/`
   - ignore missing, invalid, path-unsafe, or unrelated suggestion files and report them as warnings
   - deduplicate suggestions that describe the same memory type, source, decision, and scope
   - keep raw statements, parsed statement dumps, ledger entries, diagnostics, and proposal artifacts out of the memory handoff
   - if no eligible suggestions remain, record that no governed memory persistence was requested
   - if eligible suggestions remain, invoke `$auto-bean-memory` with the collected suggestions, source/audit context, and explicit instruction to validate eligibility and persist only approved reusable operational learning through the governed workflow
   - report the `$auto-bean-memory` result separately from import parsing, posting, validation, and final approval status
6. Review and close:
   - consolidate sub-agent results, downstream apply results, validation outcome, and `git diff`
   - keep parsed facts, ledger edits, warnings, blockers, and required user decisions separate
   - do not mark entries `done` until the user approves the final import result
   - include memory suggestions collected, ignored, deduplicated, handed to `$auto-bean-memory`, and persisted by `$auto-bean-memory`
   - do not write `.auto-bean/memory/**` directly

End with:

- processed, skipped, blocked, and user-input-needed statements
- parsed outputs written or reused
- ledger edits and status changes
- validation result and remaining decisions
- memory suggestions collected and `$auto-bean-memory` persistence result, if any
- whether the import is ready for final approval, commit, or push

Guardrails:

- Keep raw files in `statements/raw/`, parsed evidence in `statements/parsed/`, status in `statements/import-status.yml`, and governed memory in `.auto-bean/memory/`.
- Keep `$auto-bean-process` responsible for raw-to-parsed processing and first-seen account structure.
- Keep `$auto-bean-apply` responsible for postings, reconciliation, validation review, and `in_review` status.
- Do not silently reprocess current statements.
