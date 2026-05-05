---
name: auto-bean-categorize
description: Categorize transactions and identify reconciliation or deduplication decisions for exactly one assigned parsed statement or intermediate import artifact. Use as the `$auto-bean-import` parsed-evidence-to-categorization worker stage. It owns statement-scoped categorization, reconciliation findings, pending questions, and posting inputs; `$auto-bean-import` owns batching, ledger writing handoff, final review, commit, and push decisions.
---

Use this only for the parsed-evidence-to-categorization stage assigned by `$auto-bean-import`.

Inputs from `$auto-bean-import`:

- one parsed statement file or one explicit intermediate import artifact
- the matching `statements/import-status.yml` entry
- the shared raw-statement artifact prefix to use for this source's process, categorize, and import artifacts
- any relevant memory hints, reconciliation context, or user answers already approved for this artifact

Always read before acting:

- `.agents/skills/shared/parsed-statement-jq-reading.md` before inspecting large parsed statement JSON files
- `.agents/skills/shared/import-status-reading.md` before reading or updating a large `statements/import-status.yml`
- `.agents/skills/auto-bean-categorize/references/reconciliation-findings.md` for transfer, duplicate, balance, currency, or future-transfer findings

Read when needed:

- `.agents/skills/shared/parsed-statement-output.example.json` when the parsed statement shape, required fields, or field meanings are unclear
- `.agents/skills/shared/memory-access-rules.md` before using governed memory hints
- `.agents/skills/shared/question-handling-contract.md` before recording or returning pending user questions
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
   - return control to `$auto-bean-import` after all safe progress for this assigned artifact is persisted, so `$auto-bean-import` can ask the user or continue to posting through `$auto-bean-write`
   - collect eligible reusable learning throughout categorization, reconciliation, deduplication, and clarification; include memory type, source context, decision, scope, confidence or review state, supporting evidence, current-evidence checks, and why it should be reused later
4. Categorize each transaction in this artifact:
   - use current parsed facts plus governed memory hints from `.auto-bean/memory/category_mappings.json`, `.auto-bean/memory/account_mappings.json`, `.auto-bean/memory/import_sources/index.json`, matching import-source memory, and other fixed memory files only when they directly apply
   - treat parsed `account_owner` and `account_names` as statement evidence for selecting account mappings, transfer context, and memory applicability; do not treat them as ledger account names unless a current ledger check or approved mapping supports that
   - apply the shared memory access rules before reusing category, account, transfer, duplicate, naming, clarification, or import-source memory
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
   - write a user-friendly Markdown artifact under `.auto-bean/artifacts/categorize/` when the categorized result, reconciliation findings, deduplication decisions, or user-input needs are too large or structured for the parsed statement
   - use the shared raw-statement artifact prefix from `$auto-bean-import`, such as `.auto-bean/artifacts/categorize/<artifact_prefix>--categorize.md`
   - make the artifact directly fillable by a non-technical user: concise summary, clear sections, stable question IDs, checkboxes for choices, short blanks for account/category names, and explicit "leave blank if unknown" guidance where appropriate
   - include the source parsed statement path, statement/status id, categorization results, reconciliation and deduplication findings, pending and answered user questions, warnings, blockers, and memory suggestions
   - preserve any clearly labeled `Import Batch Cross-Statement Review` section that `$auto-bean-import` appended after parallel categorization; update it only when `$auto-bean-import` resumes this artifact with cross-statement context or user answers
   - keep every user-editable field visibly separated from observed facts and agent suggestions so user answers can be read back without ambiguity
   - keep artifacts factual and reviewable; do not include raw statement dumps, unrelated ledger excerpts, or accepted-history language
7. Handle clarification needs for this artifact:
   - read `.agents/skills/auto-bean-categorize/references/clarification-guidance.md` before returning any question
   - set `user_input_required: true` when account/category choice, transfer intent, duplicate suspicion, source-specific meaning, or categorization remains materially ambiguous
   - follow the shared question-handling contract; for import-invoked work, normally return question ids and the categorize artifact path so `$auto-bean-import` can keep the main thread
   - after `$auto-bean-import` supplies user answers, record the answers in the categorize artifact, resume this same artifact with the persisted artifact context and status pointer, then re-run categorization, reconciliation, and deduplication as needed
   - if the answer is still insufficient, follow the shared follow-up rule and return the remaining blocker to `$auto-bean-import`
8. Update only this artifact's status:
   - require the assigned statement to be at `ready_for_categorization` before categorization work starts
   - set `ready_for_review` after categorization, reconciliation, and deduplication work is persisted, with any user-input needs recorded in the categorize artifact

   - allowed status update from this stage is `ready_for_review`; `$auto-bean-import` advances later statuses after review, posting, validation, and approval
   - refresh the matching entry in `statements/import-status.yml`; do not create a second workflow-tracking file, and do not copy warning, question, or answer payloads into the status entry
9. Return control to `$auto-bean-import` with:
   - assigned parsed/intermediate artifact path
   - categorize artifact path if one was created or updated, including whether it needs user completion
   - short summary of what was categorized, reconciled, deduplicated, or blocked
   - categorization results and memory attribution
   - suggested transaction posting inputs for `$auto-bean-import` to pass to `$auto-bean-write` after user input is resolved
   - status changes and compact pending-question metadata for this artifact, with full warning, question, and answer details kept in the categorize artifact
   - reconciliation/deduplication findings with suggested actions
   - every persisted pending user question id and the artifact path where the full question is recorded

   
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
- Do not erase import-batch cross-statement review notes when resuming or updating a categorize artifact.
