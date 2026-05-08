---
name: auto-bean-categorize
description: Categorize transactions and identify reconciliation or deduplication decisions for exactly one assigned parsed statement JSON file or explicit import-provided Markdown handoff artifact. Use as the `$auto-bean-import` parsed-evidence-to-categorization sub-agent stage. It owns statement-scoped categorization, reconciliation findings, pending questions, and posting inputs; `$auto-bean-import` owns batching, ledger writing handoff, final review, commit, and push decisions.
---

Use this only for the parsed-evidence-to-categorization stage assigned by `$auto-bean-import`.

Inputs from `$auto-bean-import`:

- one parsed statement JSON file, or one explicit import-provided Markdown handoff artifact that points to a parsed statement and status entry
- the matching `statements/import-status.yml` entry
- the shared raw-statement artifact prefix to use for this source's process, categorize, and import artifacts
- any relevant memory hints, reconciliation context, or user answers already approved for this artifact

Always read before acting:

- `.auto-bean/memory/MEMORY.md`
- `.agents/skills/shared/sub-agent-return-examples.md`
- `.agents/skills/shared/parsed-statement-jq-reading.md` before inspecting large parsed statement JSON files
- `.agents/skills/shared/import-status-reading.md` before reading or updating a large `statements/import-status.yml`
- `.agents/skills/auto-bean-categorize/references/reconciliation-findings.md` for transfer, duplicate, balance, currency, or future-transfer findings

Read when needed:

- `.agents/skills/shared/parsed-statement-output.example.json` when the parsed statement shape, required fields, or field meanings are unclear
- `.agents/skills/shared/memory-access-rules.md` before using governed memory hints
- `.agents/skills/shared/question-handling-contract.md` before recording or returning pending user questions
- `.agents/skills/auto-bean-categorize/references/categorize-artifact-rules.md` before creating or updating a user-facing categorize artifact

Workflow:

1. Confirm the assigned scope:
   - handle only the assigned parsed/intermediate statement
   - do not scan for other parsed files or raw statements
   - do not ask for commit, push, or final import approval
2. Inspect this statement and ledger context:
   - read the assigned parsed evidence, current status entry, and supplied memory hints
   - use `$auto-bean-query` for ledger reads, account discovery, register inspection, balances, date-bounded activity, duplicate exploration, transaction existence, and account constraints
   - do not approximate those reads by grepping ledger transactions when `$auto-bean-query` can answer them
3. Create or open the working categorize artifact:
   - read `.agents/skills/auto-bean-categorize/references/categorize-artifact-rules.md`
   - create `.auto-bean/artifacts/categorize/<artifact_prefix>--categorize.md` early whenever this work may produce review details, pending or answered questions, reconciliation findings, blockers, warnings, memory suggestions, or posting inputs that should not live only in the return message
   - if an artifact already exists, use it as the working review surface and preserve any clearly labeled `Import Batch Cross-Statement Review` section
   - keep collecting safe progress in the artifact while working; for trivial no-blocker work, returning without an artifact is still allowed by the artifact rules
4. Categorize each transaction in the assigned parsed statement:
   - use current parsed facts plus relevant `.auto-bean/memory/MEMORY.md` context and governed workflow memory hints from `.auto-bean/memory/category_mappings.json`.
   - treat parsed `account_owner` and `account_names` as statement evidence for selecting account mappings, transfer context, and memory applicability; do not treat them as ledger account names unless a current ledger check or approved mapping supports that
   - apply the shared memory access rules before reusing category, account, transfer, duplicate, naming, clarification, or import-source memory
   - if memory matches under the shared strong-evidence threshold, record the matched memory path, record identity or stable summary, matched transaction facts, and resulting category/account suggestion
   - if no reliable memory matches, provide evidence-based suggestions: likely category/account, supporting statement facts, relevant ledger conventions, confidence, and plausible alternatives
   - when categorization materially affects future postings and evidence does not support one safe choice, record a pending question and continue with any remaining safe work before returning control to `$auto-bean-import`
5. Reconcile and deduplicate only this statement's parsed transactions:
   - explicitly load `.auto-bean/memory/transfer_detection.json` before transfer detection and `.auto-bean/memory/deduplication_decisions.json` before duplicate decisions
   - use `$auto-bean-query` for existing ledger activity needed to compare parsed transactions and suggested postings
   - compare parsed transactions and category/account suggestions against existing ledger entries, other candidate transactions supplied for this statement, and the parsed evidence
   - surface findings only under:
     - `likely_transfer`
     - `possible_duplicate`
     - `unbalanced`
     - `currency_risk`
     - `possible_future_transfer`
   - use `possible_future_transfer` when a transfer pattern looks strong but no existing or supplied counterpart booking matches yet
   - anchor findings in parsed facts, suggested accounts/categories, existing ledger entries, account constraints, links, metadata, imported ids, or nearby balance assertions
   - fail closed when a finding cannot be safely classified or resolved; do not guess, auto-net, auto-merge, silently drop, or rewrite candidate transactions
6. Handle clarification needs:
   - set `user_input_required: true` when account/category choice, transfer intent, duplicate suspicion, source-specific meaning, or categorization remains materially ambiguous
   - follow the shared question-handling contract; for import-invoked work, normally return question ids and the categorize artifact path so `$auto-bean-import` can keep the main thread
8. Update only this statement's status:
   - require the assigned statement to be at `categorize_ready` before categorization work starts
   - set `categorize_blocked` when required categorization, reconciliation, duplicate, transfer, or source-interpretation input is unresolved
   - set `categorize_review` after categorization, reconciliation, and deduplication work is persisted, with any user-input needs recorded in the categorize artifact

   - allowed status updates from this stage are `categorize_blocked` and `categorize_review`; `$auto-bean-import` advances later statuses after review, posting, validation, and approval
   - refresh the matching entry in `statements/import-status.yml`; do not create a second workflow-tracking file, and do not copy warning, question, or answer payloads into the status entry
9. Return control to `$auto-bean-import` using the shared compact return schema, including:
   - assigned parsed/intermediate artifact path
   - categorize artifact path if one was created or updated, including whether it needs user completion
   - short summary of what was categorized, reconciled, deduplicated, or blocked
   - categorization results and memory attribution
   - suggested transaction posting inputs for `$auto-bean-import` to pass to `$auto-bean-write` after user input is resolved
   - status changes and compact pending-question metadata for this artifact, following the shared artifact boundary
   - reconciliation/deduplication findings with suggested actions
   - every persisted pending user question id and the artifact path where the full question is recorded
   - `memory_md_suggestions`: concise suggested `.auto-bean/memory/MEMORY.md` updates for the main thread, or `[]` when none were found

Guardrails:

- Follow the shared ownership map to respect your scope strictly.
- Follow the shared workflow rules for status management, question handling, sub-agent handoff, and memory use.
- Do not edit `.auto-bean/memory/MEMORY.md` when running as a sub-agent.
- Do not bypass clarification with a best guess when ambiguity is material.
- Do not erase import-batch cross-statement review notes when resuming or updating a categorize artifact.
