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
   - require sub-agents to report parsed output paths, status changes, account-structure edits, warnings, blockers, and whether user input is needed
   - wait for all assigned processing sub-agents to finish before starting any parsed-statement handoff
3. Handoff parsed statements:
   - for each statement successfully processed to `parsed` or `parsed_with_warnings`, start one sub-agent assigned to that single parsed statement with the instruction to use `$auto-bean-apply` for posting/reconciliation work
   - run apply sub-agents sequentially: wait for the current `$auto-bean-apply` sub-agent to finish before starting the next one
   - require each `$auto-bean-apply` sub-agent to report ledger edits, status changes, reconciliation findings, validation results, blockers, reusable-learning candidates, and whether user input is needed
   - keep statements that need clarification, repair, or manual source handling out of apply work until resolved
4. Surface user input:
   - when any sub-agent or downstream skill reports missing information, risky ambiguity, unresolved reconciliation finding, or manual extraction need, ask the user a bounded question and wait for the answer instead of treating the workflow as finished or blocked
   - use the appropriate user-input tool or conversation channel; do not force clarification through a specific skill unless that skill owns the work being clarified
   - include the affected statement path, why input is needed, and the smallest useful set of choices or requested facts
   - after the user answers, restart the same processing or apply stage for the affected statement/artifact with the answer included in the assignment context
5. Review and close:
   - consolidate sub-agent results, downstream apply results, validation outcome, and `git diff`
   - keep parsed facts, ledger edits, warnings, blockers, and required user decisions separate
   - do not mark entries `done` until the user approves the final import result
   - suggest `$auto-bean-memory` only for approved reusable learning; do not write `.auto-bean/memory/**` directly

End with:

- processed, skipped, blocked, and user-input-needed statements
- parsed outputs written or reused
- ledger edits and status changes
- validation result and remaining decisions
- whether the import is ready for final approval, commit, or push

Guardrails:

- Keep raw files in `statements/raw/`, parsed evidence in `statements/parsed/`, status in `statements/import-status.yml`, and governed memory in `.auto-bean/memory/`.
- Keep `$auto-bean-process` responsible for raw-to-parsed processing and first-seen account structure.
- Keep `$auto-bean-apply` responsible for postings, reconciliation, validation review, and `in_review` status.
- Do not silently reprocess current statements.
