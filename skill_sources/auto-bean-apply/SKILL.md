---
name: auto-bean-apply
description: Apply posting, categorization, reconciliation, deduplication, clarification, and validation work for exactly one assigned parsed statement or intermediate import artifact. Use only as a bounded internal stage for `$auto-bean-import`; do not discover import work, finalize the full import, commit, push, or mark statements done.
---

Use this only for the parsed-evidence-to-working-tree stage assigned by `$auto-bean-import`.

Inputs from `$auto-bean-import`:

- one parsed statement file or one explicit intermediate import artifact
- the matching `statements/import-status.yml` entry
- any relevant memory hints, reconciliation context, or user answers already approved for this artifact

Read before acting:

- `.agents/skills/shared/memory-access-rules.md` before using governed memory hints
- `.agents/skills/auto-bean-apply/references/reconciliation-findings.md` for transfer, duplicate, balance, currency, or future-transfer findings
- `.agents/skills/auto-bean-apply/references/clarification-guidance.md` when postings remain ambiguous, unfamiliar, or blocked on user clarification

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
   - do not stop at the first ambiguous transaction when other transactions or checks can progress safely
   - categorize, draft, reconcile, deduplicate, validate, and update status for every item whose evidence supports safe action
   - collect unresolved decisions as `pending_user_questions` in the parsed/intermediate artifact or `statements/import-status.yml`, with affected transaction/source row, observed facts, plausible interpretations, risk of guessing, and the answer needed to continue
   - surface unresolved ledger edits directly in edited files when applicable with clear Beancount comments near draft placeholders or omitted postings; otherwise record explicit warnings/blocking issues in the artifact/status entry
   - ask the user only after all safe progress for this assigned artifact is persisted, so a restarted process can resume from the written artifacts instead of replaying completed work
   - collect eligible reusable learning as `memory_suggestions` throughout categorization, writing, reconciliation, deduplication, and clarification; include memory type, source context, decision, scope, confidence or review state, supporting evidence, current-evidence checks, and why it should be reused later
   - if the final response cannot carry all `memory_suggestions`, persist them in one JSON file under `.auto-bean/tmp/memory-suggestions/` named from the artifact id, status id, or source fingerprint, then return that path to `$auto-bean-import`
4. Categorize each transaction in this artifact before drafting:
   - use current parsed facts plus governed memory hints from `.auto-bean/memory/category_mappings.json`, `.auto-bean/memory/account_mappings.json`, `.auto-bean/memory/import_sources/index.json`, matching import-source memory, and other fixed memory files only when they directly apply
   - treat memory as advisory; confirm each reused category, account, transfer pattern, duplicate decision, naming convention, clarification outcome, or import-source behavior fits current evidence and current ledger context
   - if memory gives a confident match, record the matched memory path, record identity or stable summary, matched transaction facts, and resulting category/account suggestion
   - if no reliable memory matches, provide evidence-based suggestions: likely category/account, supporting statement facts, relevant ledger conventions, confidence, and plausible alternatives
   - when categorization materially affects postings and evidence does not support one safe choice, record a pending question and continue with any remaining safe work before asking
5. Draft postings for this artifact:
   - invoke `$auto-bean-write` with parsed facts, categorization results, account suggestions, relevant memory attribution, and uncertainty
   - treat `$auto-bean-write` drafted entries, validation result, duplicate/transfer/currency risks, and clarification state as inputs to this apply stage
   - describe mutations as working-tree changes for this artifact, not accepted history
6. Reconcile and deduplicate only this artifact's drafted result:
   - use `$auto-bean-query` for existing ledger activity needed to compare drafted postings
   - compare drafted postings against existing ledger entries, other candidate postings supplied for this artifact, and the parsed evidence
   - surface findings only under:
     - `likely_transfer`
     - `possible_duplicate`
     - `unbalanced`
     - `currency_risk`
     - `possible_future_transfer`
   - use `possible_future_transfer` when a transfer pattern looks strong but no existing or supplied counterpart booking matches yet
   - anchor findings in parsed facts, drafted postings, existing ledger entries, account constraints, links, metadata, imported ids, or nearby balance assertions
   - fail closed when a finding cannot be safely classified or resolved; do not guess, auto-net, auto-merge, silently drop, or rewrite candidate postings
7. Handle clarification for this artifact:
   - read `.agents/skills/auto-bean-apply/references/clarification-guidance.md` before asking anything
   - set `user_input_required: true` when account choice, transfer intent, duplicate suspicion, source-specific meaning, balancing rationale, or categorization remains materially ambiguous
   - persist all pending questions and safe partial results before asking through the appropriate user-input tool or conversation channel; include observed facts, plausible interpretations, risk of guessing, and what answer would unblock work
   - wait for the user answer; do not continue to final import approval, commit, or push while clarification is unresolved
   - after the user answers, resume this same artifact instead of returning a terminal blocked result; use `$auto-bean-write` if the answer changes drafted postings, then re-run reconciliation and validation
   - if the answer is still insufficient, ask one bounded follow-up, wait again, and resume or report the remaining blocker to `$auto-bean-import`
8. Update only this artifact's status:
   - set `in_review` after import-derived transactions for this artifact are written
   - keep `parsed` or `parsed_with_warnings` when posting work is blocked or not started
   - never set `done`
   - refresh the matching entry in `statements/import-status.yml`; do not create a second workflow-tracking file
9. Validate mutations for this artifact:
   - use the validation result from `$auto-bean-write` for transaction changes
   - re-run validation if clarification answers, finding decisions supplied by `$auto-bean-import`, or reconciliation changes alter drafted postings
   - report confirmed validation failures separately from inferred risks or follow-up concerns
10. Return control to `$auto-bean-import` with:
   - assigned parsed/intermediate artifact path
   - short summary of what changed and why
   - affected files and `git diff -- <paths>` guidance or equivalent diff summary
   - categorization results and memory attribution
   - drafted ledger edits for this artifact
   - status change for this artifact
   - reconciliation/deduplication findings with suggested actions
   - validation result
   - every persisted pending user question, with the exact question/reason and where it was recorded
   - `memory_suggestions`: every eligible reusable-learning candidate for `$auto-bean-import` to consider via `$auto-bean-memory`, or `[]` when none were found
   - `memory_suggestion_files`: any `.auto-bean/tmp/memory-suggestions/*.json` files created because suggestions were too large for the response

Guardrails:

- Do not discover, batch, or orchestrate import work.
- Do not mark statements `done`.
- Do not request commit or push approval.
- Do not apply a reconciliation finding decision unless `$auto-bean-import` supplies the explicit user answer for this artifact.
- Do not bypass clarification with a best guess when ambiguity is material.
- Do not write `.auto-bean/memory/**`; report possible reusable learning back to `$auto-bean-import` so it can decide whether to invoke `$auto-bean-memory`.
- Do not imply working-tree mutations have been accepted into history.
- Do not ask for user input before persisting all safe progress and making unresolved requirements visible in the relevant artifacts.
