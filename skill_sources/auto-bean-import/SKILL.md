---
name: auto-bean-import
description: Orchestrate statement imports from raw statement discovery through delegated processing, delegated categorization, user-input surfacing, ledger posting, validation review, and final summary. Use when the user asks to import statements, process new raw statements, run the import workflow, or continue work from `statements/raw/` and `statements/import-status.yml`.
---

Use this as the user-facing import entrypoint. Delegate mechanics to narrower skills instead of duplicating their procedures.


Read before acting:
- `.agents/skills/shared/import-status.example.yml`
- `.agents/skills/shared/import-status-reading.md` before reading or updating a large `statements/import-status.yml`
- `.agents/skills/auto-bean-import/references/import-artifact-contract.md`
- `.agents/skills/shared/question-handling-contract.md` before surfacing or resuming process, categorize, first-seen-account, or write-stage questions
- `.agents/skills/shared/memory-access-rules.md` before using governed memory hints, especially `import_source_behavior` memory under `.auto-bean/memory/import_sources/`

Workflow:

1. Discover unprocessed work:
   - inspect `statements/raw/`, `statements/parsed/`, and `statements/import-status.yml`
   - create or refresh one import-owned Markdown artifact per raw statement under `.auto-bean/artifacts/import/` according to the shared import artifact contract
   - use the same deterministic raw-statement filename prefix for that statement's process, categorize, and import artifacts
   - fingerprint supported raw files: `.pdf`, `.csv`, `.xlsx`, `.xls`
   - inspect `.auto-bean/memory/import_sources/index.json` and select only narrow matching `import_source_behavior` records by source identity, institution, raw-statement account owner, raw-statement account names, account hints, statement shape, filename pattern, or fingerprint
   - keep matched import-source memory advisory and statement-scoped; record reuse attribution in the import-owned artifact when it influences processing handoff, first-seen account inspection, or memory handoff
   - send raw files to `$auto-bean-process` only when they have no current parsed output, missing status, changed fingerprint, eligible `ready` status, or an explicit user reprocess request
   - treat `ready` as eligible for automatic processing only when `manual_resolution_required` is not true and `process_attempts` is below 2 for the current fingerprint
   - when a current-fingerprint `ready` entry has `process_attempts` of 2 or more, keep it out of automatic processing, preserve the last failure reason and process artifact, and surface the manual-resolution requirement to the user
   - allow an explicit user reprocess request to retry a manually held `ready` entry; record the new attempt and reason instead of clearing prior retry history silently
   - continue orchestration for existing entries at `parsed`, `parsed_with_warning`, `account_inspection`, `ready_for_categorization`, `ready_for_review`, `ready_to_write`, or `final_review`
   - skip entries already current at `done` unless the user explicitly requests rework
2. Use sub-agents in parallel for statement processing:
   - Spawn in parallel one sub-agent per statement
   - give each sub-agent the source path, current status entry including retry metadata, expected parsed-output path or naming rule, the shared raw-statement artifact prefix, any narrowly matched `import_source_behavior` memory path or summary, and the instruction to use `$auto-bean-process`
   - require sub-agents to follow the shared question-handling contract and to report parsed output paths, status changes, warning/blocker presence flags, process artifacts under `.auto-bean/artifacts/process/` using the shared prefix; full warning, question, and answer details stay in the process artifact
   - wait for all assigned processing sub-agents to finish before starting any parsed-statement handoff
3. Resolve process questions and update intermediate statements:
   - inspect every reported process artifact under `.auto-bean/artifacts/process/`
   - for `parsed_with_warning`, read the artifact produced by `$auto-bean-process` and ask the user any bounded questions needed to make the parsed intermediate statement trustworthy before downstream work
   - use the shared question-handling contract for question shape, batching, answer capture, and stage resume
   - after the user answers, update the relevant intermediate parsed statement and status entry only for resulting operational changes, and record the answer in the process artifact when it resolves or changes parsed evidence
   - update the statement's import-owned artifact with unresolved and answered process question ids, process artifact paths, affected paths, and resume decisions; keep the full warning, question, and answer payloads in the process artifact, and do not copy current status, status transitions, full parsed payloads, or replace process-owned artifacts
   - resume `$auto-bean-process` only when the answer requires parser-specific regeneration or normalization that should stay inside the raw-to-parsed worker boundary
   - when a `parsed` statement needs no process-stage user input, mark it `account_inspection`
   - when all `parsed_with_warning` warnings or process questions are resolved enough for downstream work, make the appropriate artifact and status changes and mark it `account_inspection`
   - keep statements that still have unresolved process questions out of first-seen derivation, categorization, and posting work
   - once all process questions are resolved, close all the sub-agents that ran `$auto-bean-process` for this batch of statements; do not keep them alive for the rest of the workflow
4. Derive first-seen accounts:
   - for each statement with resolved process questions and status `account_inspection`, inspect `beancount/accounts.beancount` first, then `ledger.beancount` and included `beancount/**` files for existing `open` directives and account names
   - before proposing account-structure changes, read any matching `import_source_behavior` memory selected during discovery or reported by `$auto-bean-process`
   - use import-source behavior memory to recognize stable institution identity, raw-statement account owner, raw-statement account names, account fragments, account type hints, operating currency, recurring statement descriptors, and duplicate-risk checks that are useful for account inspection
   - verify every memory-derived hint against the current parsed statement evidence and current ledger state before using it in a first-seen account decision
   - classify inferred accounts as `existing_account`, `first_seen_candidate`, or `blocked_inference`
   - consider only banking, credit card, loans, cash, and investment account types for first-seen structure inference
   - during first-seen account inspection, infer only institution-owned balance-sheet accounts; leave expense, income, and other transaction categories to `$auto-bean-categorize`
   - infer Beancount-safe account names and minimal supporting directives only when institution, raw-statement account owner or account names, account identity, type hints, and currency provide strong evidence
   - current parsed statement evidence and current ledger state remain authoritative; memory may provide hints, not authority
   - ignore or flag memory that is missing, malformed, stale, too broad, inconsistent with parsed evidence, inconsistent with existing accounts, or outside the matched statement source
   - when top-level branch, account identity, currency, duplicate risk, mutation target, or syntax is unclear, ask the user a bounded question before mutating account structure
   - before writing any new `open` directive, present the exact proposed directive, target file, supporting parsed evidence, and reason the account appears first-seen; ask the user to approve or correct it, then wait for the response
   - record each proposed, approved, rejected, or written first-seen account decision in the statement's import-owned artifact with evidence references, memory attribution or rejection notes, target file, user approval context, and validation references
   - after the user approves or corrects the proposal, write only the approved account-opening structure and minimal supporting directives such as missing operating currencies; prefer `beancount/accounts.beancount` and explain any fallback target
   - avoid duplicate directives and keep mutations deterministic for the same parsed input and ledger state
   - run `./scripts/validate-ledger.sh` or `./.venv/bin/bean-check ledger.beancount` after account-structure edits
   - after first-seen account inspection, any needed account-structure edits, and validation are complete, mark the statement `ready_for_categorization`
   - keep statements with unresolved first-seen account questions out of posting work until resolved
5. Handoff parsed statements to `$auto-bean-categorize` sub-agents:
   - for each statement at `ready_for_categorization` with resolved process and first-seen account questions, start one sub-agent assigned to that single parsed statement with the instruction to use `$auto-bean-categorize` for categorization, reconciliation, and deduplication work
   - run categorize sub-agents in parallel, then wait for all to finish before starting any categorize-to-post work
   - require each `$auto-bean-categorize` sub-agent to follow the shared question-handling contract and to report categorization results, posting inputs, status changes or compact pending-question metadata, reconciliation findings, blocker presence flags, categorize artifact paths using the shared prefix, persisted pending user question ids; full warning, question, and answer details stay in the categorize artifact
   - keep statements that need clarification, repair, or manual source handling out of posting and final approval until resolved
   - once all categorize-assigned sub-agents finish, close them; do not keep them alive for the rest of the workflow
6. Review cross-statement transfer and duplicate candidates:
   - before surfacing categorize findings to the user, read every produced categorize artifact and returned posting input for statements in the same import batch that reached `ready_for_review`
   - compare candidate postings across statements for likely transfers between imported accounts, mirror-image amounts, nearby dates, matching currencies, complementary descriptions, shared references, fees, FX legs, or account-pair patterns
   - compare batch candidates against existing ledger activity when needed through `$auto-bean-query`; do not approximate ledger reads by grepping when `$auto-bean-query` can answer them
   - treat this as a batch-level review that augments, but does not replace, each statement-scoped `$auto-bean-categorize` result
   - record only reviewable cross-statement candidates; do not auto-drop, auto-net, or silently mark either side as duplicate without strong evidence or approved user input
   - when a likely transfer or possible duplicate spans multiple categorize artifacts, update each affected categorize artifact with a clearly labeled `Import Batch Cross-Statement Review` section containing the paired artifact paths, transaction ids or stable row references, matched facts, confidence, suggested deduplication or transfer-handling action, and any bounded user question id
   - update each affected import-owned artifact with the cross-statement finding summary, affected categorize artifact paths, question ids, and posting-decision impact; do not copy full categorization analysis into import-owned artifacts
   - if a cross-statement match changes a prior posting suggestion or deduplication decision materially, either update the affected categorize artifact directly with the import-batch review note or resume the same `$auto-bean-categorize` artifact with the cross-statement context when statement-local categorization must be recomputed
   - keep statements with unresolved cross-statement transfer or duplicate questions out of `ready_to_write`
7. Surface categorize user input:
   - for each statement at `ready_for_review`, read the artifact produced by `$auto-bean-categorize`
   - when any sub-agent or downstream skill reports missing information, risky ambiguity, unresolved reconciliation finding, or manual extraction need, follow the shared question-handling contract
   - include cross-statement transfer or duplicate candidates from the import-batch review when batching questions, so the user can approve one coherent transfer/deduplication decision across all affected statements
   - when a categorize artifact path is reported under `.auto-bean/artifacts/categorize/`, present that path to the user as the fillable review surface and ask them either to answer in conversation or complete the artifact
   - ask the user the collected bounded question or question set and wait for the answer instead of treating the workflow as finished or blocked
   - use the appropriate user-input tool or conversation channel; do not force clarification through a specific skill unless that skill owns the work being clarified
   - after the user answers or fills the artifact, read the completed artifact if applicable, record conversation answers in the relevant individual artifact, then make the appropriate artifact and status changes or resume the same first-seen derivation or categorize stage for the affected statement/artifact with the answer and existing persisted artifacts included in the assignment context
   - update the statement's import-owned artifact with categorize artifact paths, answered question ids, unresolved blocker summaries, cross-statement transfer or duplicate decisions, memory-suggestion provenance, and posting decisions; keep the full warning, question, and answer payloads in the categorize artifact, and do not copy status fields, full categorization analysis, or replace categorize-owned artifacts
   - when categorization output and required user input are resolved, mark the statement `ready_to_write`
8. Post categorized transactions:
   - for each parsed statement at `ready_to_write`, take back the main thread and invoke `$auto-bean-write` with parsed records, category/account suggestions, reconciliation and deduplication decisions, memory attribution, and any approved user answers
   - record each `$auto-bean-write` handoff decision in the statement's import-owned artifact before invoking it, then record references to the returned mutation package and validation result
   - keep `$auto-bean-write` focused on drafting Beancount transaction entries and transaction-specific validation; do not make `$auto-bean-categorize` draft ledger mutations
   - if `$auto-bean-write` returns a bounded clarification question, use the shared question-handling contract to ask in the main import thread, record the question and answer in the import-owned artifact for that statement, then resume `$auto-bean-write` with the answer and the existing categorize artifact context plus status pointer
   - set `final_review` only after import-derived transactions for that statement are written and validated
9. Verify, review and close:
   - Use `$auto-bean-query` to verify the posted transactions between the ledger and the parsed statement evidence; Explicitly check the accounts balances against the parsed statement.
   - consolidate sub-agent results, process question outcomes, first-seen account derivation, downstream categorize results, write results, validation outcome
   - reconcile `statements/import-status.yml` against per-statement artifact references before presenting final review; fail closed on source, prefix, or artifact-path conflicts
   - keep parsed facts, first-seen account edits, ledger postings, warnings, blockers, questions, answers, and required user decisions separate, with warning/question/answer details kept in the relevant individual artifacts
   - for statements at `final_review`, ask the user to validate the final import result
   - mark entries `done` only after the user approves the final import result
   - keep commit and push finalization orchestrator-owned: after import approval and any `done` transitions, `$auto-bean-import` is the only workflow stage that may ask for or act on commit or push approval for import-derived mutations
10. Hand off governed memory persistence to `$auto-bean-memory` via sub-agent:
   - collect all workflow artifacts produced during this import: process artifacts under `.auto-bean/artifacts/process/`, categorize artifacts under `.auto-bean/artifacts/categorize/`, and statement-scoped import-owned artifacts under `.auto-bean/artifacts/import/`
   - Spawn a sub-agent that invokes the `$auto-bean-memory` skill with those artifact paths, asking it to persist any reusable learning as governed memory for future import work; do not call `$auto-bean-memory` separately for each artifact.
   - report the `$auto-bean-memory` result separately from import parsing, posting, validation, and final approval status


End with:

- processed, skipped, blocked, and user-input-needed statements
- parsed outputs written or reused
- first-seen account edits, ledger posting edits, and status changes
- import-owned artifact paths and whether their source, prefix, and artifact references are consistent with `statements/import-status.yml`
- validation result and remaining decisions
- memory suggestions collected and `$auto-bean-memory` persistence result, if any
- whether the import is ready for final approval, or whether orchestrator-owned commit or push approval is needed

Guardrails:

- Keep raw files in `statements/raw/`, parsed evidence in `statements/parsed/`, status in `statements/import-status.yml`, and governed memory in `.auto-bean/memory/`.
- Keep statement-scoped import-owned artifacts under `.auto-bean/artifacts/import/`; `$auto-bean-import` is the only stage that creates or updates them.
- Keep each import-owned artifact at the decision/provenance level: link to process and categorize artifacts and summarize only import-owned decisions, import-brokered questions and answers, memory suggestions, blockers, and handoffs. Do not copy worker-owned warning, question, or answer payloads into the import artifact.
- Store operational progress only in `statements/import-status.yml`; import-owned artifacts store stable decisions, provenance, artifact links, and import-brokered answers.
- Keep `$auto-bean-process` responsible only for raw-to-parsed processing, process artifacts, and process-stage memory suggestions.
- Keep `$auto-bean-import` responsible for process question surfacing, intermediate-statement updates, moving parsed statements to `account_inspection`, first-seen account derivation, moving inspected statements to `ready_for_categorization`, cross-statement transfer and duplicate review after parallel categorization, categorize artifact review, moving reviewed categorization output to `ready_to_write`, invoking `$auto-bean-write`, setting `final_review`, final user approval to `done`, and the final governed memory handoff.
- `$auto-bean-import` may update categorize artifacts only for clearly labeled import-batch cross-statement review notes, user answers it brokered, or resume context needed by `$auto-bean-categorize`; it must not rewrite statement-local categorization analysis outside that scope.
- Keep `$auto-bean-categorize` responsible only for categorization, reconciliation, deduplication, user-input needs, and memory suggestions.
- Keep `$auto-bean-write` responsible for posting categorized transactions and transaction-specific validation after `$auto-bean-import` resumes the main thread; commit and push authority remains with `$auto-bean-import` during import workflows.
- Do not silently reprocess current statements or repeatedly retry `ready` statements that have reached the current-fingerprint manual-resolution threshold.
