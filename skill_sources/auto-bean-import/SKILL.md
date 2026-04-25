---
name: auto-bean-import
description: Orchestrate statement imports from raw statement discovery through delegated processing, delegated categorization, user-input surfacing, ledger posting, validation review, and final summary. Use when the user asks to import statements, process new raw statements, run the import workflow, or continue work from `statements/raw/` and `statements/import-status.yml`.
---

Use this as the user-facing import entrypoint. Delegate mechanics to narrower skills instead of duplicating their procedures.


Read before acting:
- `.agents/skills/shared/import-status.example.yml`

Workflow:

1. Discover unprocessed work:
   - inspect `statements/raw/`, `statements/parsed/`, and `statements/import-status.yml`
   - fingerprint supported raw files: `.pdf`, `.csv`, `.xlsx`, `.xls`
   - send raw files to `$auto-bean-process` only when they have no current parsed output, missing status, changed fingerprint, eligible `ready` status, or an explicit user reprocess request
   - treat `ready` as eligible for automatic processing only when `manual_resolution_required` is not true and `process_attempts` is below 2 for the current fingerprint
   - when a current-fingerprint `ready` entry has `process_attempts` of 2 or more, keep it out of automatic processing, preserve the last failure reason and process question artifact, and surface the manual-resolution requirement to the user
   - allow an explicit user reprocess request to retry a manually held `ready` entry; record the new attempt and reason instead of clearing prior retry history silently
   - continue orchestration for existing entries at `parsed`, `parsed_with_warning`, `account_inspection`, `ready_for_categorization`, `ready_for_review`, `ready_to_write`, or `final_review`
   - skip entries already current at `done` unless the user explicitly requests rework
2. Use sub-agents for statement work:
   - assign each sub-agent one raw statement
   - give each sub-agent the source path, current status entry including retry metadata, expected parsed-output path or naming rule, and the instruction to use `$auto-bean-process`
   - require sub-agents to persist all safe progress without asking the user directly, and to report parsed output paths, status changes, warnings, blockers, process question artifacts under `.auto-bean/artifacts/process/`, `memory_suggestions`, and `memory_suggestion_files`
   - wait for all assigned processing sub-agents to finish before starting any parsed-statement handoff
3. Resolve process questions and update intermediate statements:
   - inspect every reported process question artifact under `.auto-bean/artifacts/process/`
   - for `parsed_with_warning`, read the artifact produced by `$auto-bean-process` and ask the user any bounded questions needed to make the parsed intermediate statement trustworthy before downstream work
   - include the affected statement path, observed facts, why input is needed, and the smallest useful set of choices or requested facts
   - after the user answers, update the relevant intermediate parsed statement, status entry, and process artifact when the answer resolves or changes parsed evidence
   - resume `$auto-bean-process` only when the answer requires parser-specific regeneration or normalization that should stay inside the raw-to-parsed worker boundary
   - when a `parsed` statement needs no process-stage user input, mark it `account_inspection`
   - when all `parsed_with_warning` warnings or process questions are resolved enough for downstream work, make the appropriate artifact/status changes and mark it `account_inspection`
   - keep statements that still have unresolved process questions out of first-seen derivation, categorization, and posting work
4. Derive first-seen accounts:
   - for each statement with resolved process questions and status `account_inspection`, inspect `beancount/accounts.beancount` first, then `ledger.beancount` and included `beancount/**` files for existing `open` directives and account names
   - classify inferred accounts as `existing_account`, `first_seen_candidate`, or `blocked_inference`
   - consider only banking, credit card, loans, cash, and investment account types for first-seen structure inference
   - do not infer mutable categories such as expense accounts
   - infer Beancount-safe account names and minimal supporting directives only when institution, account identity, type hints, and currency provide strong evidence
   - current parsed statement evidence and current ledger state remain authoritative; memory may provide hints, not authority
   - when top-level branch, account identity, currency, duplicate risk, mutation target, or syntax is unclear, ask the user a bounded question before mutating account structure
   - before writing any new `open` directive, present the exact proposed directive, target file, supporting parsed evidence, and reason the account appears first-seen; ask the user to approve or correct it, then wait for the response
   - after the user approves or corrects the proposal, write only the approved account-opening structure and minimal supporting directives such as missing operating currencies; prefer `beancount/accounts.beancount` and explain any fallback target
   - avoid duplicate directives and keep mutations deterministic for the same parsed input and ledger state
   - run `./scripts/validate-ledger.sh` or `./.venv/bin/bean-check ledger.beancount` after account-structure edits
   - after first-seen account inspection, any needed account-structure edits, and validation are complete, mark the statement `ready_for_categorization`
   - keep statements with unresolved first-seen account questions out of posting work until resolved
5. Handoff parsed statements:
   - for each statement at `ready_for_categorization` with resolved process and first-seen account questions, start one sub-agent assigned to that single parsed statement with the instruction to use `$auto-bean-categorize` for categorization, reconciliation, and deduplication work
   - run categorize sub-agents sequentially: wait for the current `$auto-bean-categorize` sub-agent to finish before starting the next one
   - require each `$auto-bean-categorize` sub-agent to persist all safe progress before requesting user input, and to report categorization results, posting inputs, status changes or pending-question metadata, reconciliation findings, blockers, categorize artifact paths, persisted pending user questions, `memory_suggestions`, and `memory_suggestion_files`
   - keep statements that need clarification, repair, or manual source handling out of posting and final approval until resolved
6. Surface categorize user input:
   - for each statement at `ready_for_review`, read the artifact produced by `$auto-bean-categorize`
   - when any sub-agent or downstream skill reports missing information, risky ambiguity, unresolved reconciliation finding, or manual extraction need, first verify the relevant artifact/status/file records all safe progress and clearly names what remains required from the user
   - when a categorize artifact path is reported under `.auto-bean/artifacts/categorize/`, present that path to the user as the fillable review surface and ask them either to answer in conversation or complete the artifact
   - ask the user the collected bounded question or question set and wait for the answer instead of treating the workflow as finished or blocked
   - use the appropriate user-input tool or conversation channel; do not force clarification through a specific skill unless that skill owns the work being clarified
   - include the affected statement path, why input is needed, and the smallest useful set of choices or requested facts
   - after the user answers or fills the artifact, read the completed artifact if applicable, then make the appropriate artifact/status changes or resume the same first-seen derivation or categorize stage for the affected statement/artifact with the answer and existing persisted artifacts included in the assignment context
   - when categorization output and required user input are resolved, mark the statement `ready_to_write`
7. Post categorized transactions:
   - for each statement at `ready_to_write`, take back the main thread and invoke `$auto-bean-write` with parsed facts, category/account suggestions, reconciliation and deduplication decisions, memory attribution, and any approved user answers
   - keep `$auto-bean-write` focused on drafting Beancount transaction entries and transaction-specific validation; do not make `$auto-bean-categorize` draft ledger mutations
   - if `$auto-bean-write` returns a bounded clarification question, ask the user in the main import thread, then resume `$auto-bean-write` with the answer and the existing categorize artifact/status context
   - set `final_review` only after import-derived transactions for that statement are written and validated
8. Review and close:
   - consolidate sub-agent results, process question outcomes, first-seen account derivation, downstream categorize results, write results, validation outcome, and `git diff`
   - keep parsed facts, first-seen account edits, ledger postings, warnings, blockers, and required user decisions separate
   - for statements at `final_review`, ask the user to validate the final import result
   - mark entries `done` only after the user approves the final import result
   - keep commit and push finalization orchestrator-owned: after import approval and any `done` transitions, `$auto-bean-import` is the only workflow stage that may ask for or act on commit or push approval for import-derived mutations
9. Collect and govern memory suggestions at the end:
   - collect `memory_suggestions` returned by every `$auto-bean-process` and `$auto-bean-categorize` sub-agent, including resumed stages after user answers
   - read any returned `memory_suggestion_files` only when the path stays under `.auto-bean/tmp/memory-suggestions/`
   - collect produced categorize artifact paths returned by `$auto-bean-categorize` and read only those under `.auto-bean/artifacts/categorize/`
   - before final response, look for memory suggestion files created during this import under `.auto-bean/tmp/memory-suggestions/`, include eligible files not already reported by sub-agents, and ignore unrelated files with a warning
   - before final response, look for categorize artifacts created during this import under `.auto-bean/artifacts/categorize/`, include eligible files not already reported by sub-agents, and ignore unrelated files with a warning
   - ignore missing, invalid, path-unsafe, or unrelated suggestion files and report them as warnings
   - extract any explicit memory suggestions or user-approved reusable decisions from completed categorize artifacts, keeping the artifact path as supporting evidence
   - deduplicate suggestions that describe the same memory type, source, decision, and scope
   - keep raw statements, parsed statement dumps, ledger entries, diagnostics, and proposal artifacts out of the memory handoff
   - if no eligible suggestions or completed categorize artifacts with memory-relevant answers remain, record that no governed memory persistence was requested
   - if eligible suggestions or completed categorize artifacts with memory-relevant answers remain, invoke `$auto-bean-memory` with the collected suggestions, eligible memory suggestion artifacts, completed categorize artifacts as source/audit context, and explicit instruction to validate eligibility and persist only approved reusable operational learning through the governed workflow
   - report the `$auto-bean-memory` result separately from import parsing, posting, validation, and final approval status
   - include memory suggestions and categorize artifacts collected, ignored, deduplicated, handed to `$auto-bean-memory`, and persisted by `$auto-bean-memory`
   - do not write `.auto-bean/memory/**` directly

End with:

- processed, skipped, blocked, and user-input-needed statements
- parsed outputs written or reused
- first-seen account edits, ledger posting edits, and status changes
- validation result and remaining decisions
- memory suggestions collected and `$auto-bean-memory` persistence result, if any
- whether the import is ready for final approval, or whether orchestrator-owned commit or push approval is needed

Guardrails:

- Keep raw files in `statements/raw/`, parsed evidence in `statements/parsed/`, status in `statements/import-status.yml`, and governed memory in `.auto-bean/memory/`.
- Keep `$auto-bean-process` responsible only for raw-to-parsed processing, process question artifacts, and process-stage memory suggestions.
- Keep `$auto-bean-import` responsible for process question surfacing, intermediate-statement updates, moving parsed statements to `account_inspection`, first-seen account derivation, moving inspected statements to `ready_for_categorization`, categorize artifact review, moving reviewed categorization output to `ready_to_write`, invoking `$auto-bean-write`, setting `final_review`, final user approval to `done`, and the final governed memory handoff.
- Keep `$auto-bean-categorize` responsible only for categorization, reconciliation, deduplication, user-input needs, and memory suggestions.
- Keep `$auto-bean-write` responsible for posting categorized transactions and transaction-specific validation after `$auto-bean-import` resumes the main thread; commit and push authority remains with `$auto-bean-import` during import workflows.
- Do not silently reprocess current statements or repeatedly retry `ready` statements that have reached the current-fingerprint manual-resolution threshold.
