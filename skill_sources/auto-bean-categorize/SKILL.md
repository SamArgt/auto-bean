---
name: auto-bean-categorize
description: Categorize transactions and identify reconciliation or deduplication decisions for exactly one assigned parsed statement or intermediate import artifact. Use only as a bounded internal stage for `$auto-bean-import`; do not write ledger postings, finalize the full import, commit, push, or mark statements done.
---

Use this only for the parsed-evidence-to-categorization stage assigned by `$auto-bean-import`.

Inputs from `$auto-bean-import`:

- one parsed statement file or one explicit intermediate import artifact
- the matching `statements/import-status.yml` entry
- the shared raw-statement artifact prefix to use for this source's process, categorize, and import artifacts
- any relevant memory hints, reconciliation context, or user answers already approved for this artifact

Read before acting:

- `.agents/skills/shared/memory-access-rules.md` before using governed memory hints
- `.agents/skills/shared/parsed-statement-output.example.json`
- `.agents/skills/shared/parsed-statement-jq-reading.md` before inspecting large parsed statement artifacts
- `.agents/skills/shared/question-handling-contract.md` before recording or returning pending user questions
- `.agents/skills/auto-bean-categorize/references/reconciliation-findings.md` for transfer, duplicate, balance, currency, or future-transfer findings
- `.agents/skills/auto-bean-categorize/references/clarification-guidance.md` when categorization, reconciliation, or deduplication remains ambiguous, unfamiliar, or blocked on user clarification
- `.agents/skills/auto-bean-categorize/references/categorize-artifact.example.md` before creating or updating a user-facing categorize artifact

Workflow:

1. Confirm the assigned scope:
   - handle only the assigned parsed/intermediate artifact
   - do not scan for other parsed files or raw statements
   - do not decide which artifact should run next
   - do not ask for commit, push, or final import approval
2. Inspect this artifact and ledger context:
   - read the assigned parsed evidence, current status entry, and supplied memory hints
   - use `$auto-bean-query` for ledger reads, account discovery, register inspection, balances, date-bounded activity, duplicate exploration, transaction existence, and account constraints
   - do not approximate those reads by grepping ledger transactions when `$auto-bean-query` can answer them
3. Work forward while collecting questions:
   - follow the shared question-handling contract
   - categorize, reconcile, deduplicate, and record every item whose evidence supports safe analysis
   - collect unresolved decisions in a categorize artifact under `.auto-bean/artifacts/categorize/`
   - record explicit warnings, blocking issues, and requested user inputs in the artifact/status entry; do not add Beancount placeholders or draft ledger mutations
   - return control to `$auto-bean-import` after all safe progress for this assigned artifact is persisted, so `$auto-bean-import` can ask the user or continue to posting through `$auto-bean-write`
   - collect eligible reusable learning as `memory_suggestions` throughout categorization, reconciliation, deduplication, and clarification; include memory type, source context, decision, scope, confidence or review state, supporting evidence, current-evidence checks, and why it should be reused later
   - keep memory candidates in the returned `memory_suggestions` structure and, when useful for auditability, include them in the categorize artifact; do not create a separate temporary memory-suggestions artifact
4. Categorize each transaction in this artifact:
   - use current parsed facts plus governed memory hints from `.auto-bean/memory/category_mappings.json`, `.auto-bean/memory/account_mappings.json`, `.auto-bean/memory/import_sources/index.json`, matching import-source memory, and other fixed memory files only when they directly apply
   - treat memory as advisory; confirm each reused category, account, transfer pattern, duplicate decision, naming convention, clarification outcome, or import-source behavior fits current evidence and current ledger context
   - if memory gives a confident match, record the matched memory path, record identity or stable summary, matched transaction facts, and resulting category/account suggestion
   - if no reliable memory matches, provide evidence-based suggestions: likely category/account, supporting statement facts, relevant ledger conventions, confidence, and plausible alternatives
   - when categorization materially affects future postings and evidence does not support one safe choice, record a pending question and continue with any remaining safe work before returning control to `$auto-bean-import`
5. Reconcile and deduplicate only this artifact's parsed transactions:
   - use `$auto-bean-query` for existing ledger activity needed to compare parsed transactions and suggested postings
   - compare parsed transactions and category/account suggestions against existing ledger entries, other candidate transactions supplied for this artifact, and the parsed evidence
   - surface findings only under:
     - `likely_transfer`
     - `possible_duplicate`
     - `unbalanced`
     - `currency_risk`
     - `possible_future_transfer`
   - use `possible_future_transfer` when a transfer pattern looks strong but no existing or supplied counterpart booking matches yet
   - anchor findings in parsed facts, suggested accounts/categories, existing ledger entries, account constraints, links, metadata, imported ids, or nearby balance assertions
   - fail closed when a finding cannot be safely classified or resolved; do not guess, auto-net, auto-merge, silently drop, or rewrite candidate transactions
6. Create or update a categorize artifact when useful:
   - read `.agents/skills/auto-bean-categorize/references/categorize-artifact.example.md` first
   - write a user-friendly Markdown artifact under `.auto-bean/artifacts/categorize/` when the categorized result, reconciliation findings, deduplication decisions, or user-input needs are too large or structured for the parsed artifact/status entry
   - use the shared raw-statement artifact prefix from `$auto-bean-import`, such as `.auto-bean/artifacts/categorize/<artifact_prefix>--categorize.md`
   - make the artifact directly fillable by a non-technical user: concise summary, clear sections, stable question IDs, checkboxes for choices, short blanks for account/category names, and explicit "leave blank if unknown" guidance where appropriate
   - include the source parsed artifact, statement/status id, categorization results, reconciliation and deduplication findings, pending user questions, and memory suggestions
   - keep every user-editable field visibly separated from observed facts and agent suggestions so user answers can be read back without ambiguity
   - keep artifacts factual and reviewable; do not include raw statement dumps, unrelated ledger excerpts, or accepted-history language
7. Handle clarification needs for this artifact:
   - read `.agents/skills/auto-bean-categorize/references/clarification-guidance.md` before returning any question
   - set `user_input_required: true` when account/category choice, transfer intent, duplicate suspicion, source-specific meaning, or categorization remains materially ambiguous
   - follow the shared question-handling contract before returning control; normally return the question set so `$auto-bean-import` can keep the main thread unless it explicitly delegated user interaction
   - after `$auto-bean-import` supplies user answers, resume this same artifact with the persisted artifact/status context, then re-run categorization, reconciliation, and deduplication as needed
   - if the answer is still insufficient, follow the shared follow-up rule and return the remaining blocker to `$auto-bean-import`
8. Update only this artifact's status:
   - require the assigned statement to be at `ready_for_categorization` before categorization work starts
   - set `ready_for_review` after categorization, reconciliation, and deduplication work is persisted, including any user-input needs in the artifact/status entry

   - never set `ready_to_write`, `final_review`, or `done`
   - refresh the matching entry in `statements/import-status.yml`; do not create a second workflow-tracking file
9. Return control to `$auto-bean-import` with:
   - assigned parsed/intermediate artifact path
   - categorize artifact path if one was created or updated, including whether it needs user completion
   - short summary of what was categorized, reconciled, deduplicated, or blocked
   - categorization results and memory attribution
   - suggested transaction posting inputs for `$auto-bean-import` to pass to `$auto-bean-write` after user input is resolved
   - status changes or pending-question metadata for this artifact
   - reconciliation/deduplication findings with suggested actions
   - every persisted pending user question, with the exact question/reason and where it was recorded
   - `memory_suggestions`: every eligible reusable-learning candidate for `$auto-bean-import` to consider via `$auto-bean-memory`, or `[]` when none were found

Guardrails:

- Do not discover, batch, or orchestrate import work.
- Do not invoke `$auto-bean-write`.
- Do not write or edit Beancount ledger entries.
- Do not mark statements `done`.
- Do not set statements `ready_to_write` or `final_review`; those statuses belong to `$auto-bean-import` after categorize review and transaction writing.
- Do not request commit or push approval.
- Do not apply a reconciliation finding decision unless `$auto-bean-import` supplies the explicit user answer for this artifact.
- Do not bypass clarification with a best guess when ambiguity is material.
- Do not write `.auto-bean/memory/**`; report possible reusable learning back to `$auto-bean-import` so it can decide whether to invoke `$auto-bean-memory`.
- Do not imply working-tree mutations have been accepted into history.
- Do not ask for user input before following the shared question-handling contract and making unresolved requirements visible in the relevant artifacts.
