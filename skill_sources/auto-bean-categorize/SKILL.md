---
name: auto-bean-categorize
description: Categorize one assigned parsed statement or import handoff artifact. Suggest categories, using memory, ledger context, and web search for unknown merchants; identify reconciliation/deduplication findings, questions, and posting inputs for `$auto-bean-import`.
---

Use this only for the parsed-evidence-to-categorization stage assigned by `$auto-bean-import`.

Inputs from `$auto-bean-import`:

- one parsed statement JSON file, or one explicit import-provided Markdown handoff artifact that points to a parsed statement and status entry
- the matching `statements/import-status.yml` entry
- the shared raw-statement artifact prefix to use for this source's process, categorize, and import artifacts
- any relevant memory hints, reconciliation context, or user answers already approved for this artifact

MUST read before acting:

- `.auto-bean/memory/MEMORY.md`
- `.agents/skills/shared/workflow-rules.md`
- `.agents/skills/shared/parsed-statement-jq-reading.md` before inspecting large parsed statement JSON files
- `.agents/skills/shared/import-status-reading.md` before reading or updating a large `statements/import-status.yml`
- `.agents/skills/auto-bean-categorize/references/reconciliation-findings.md` for transfer, duplicate, balance, currency, or future-transfer findings

Read when needed:

- `.agents/skills/shared/parsed-statement-output.example.json` MUST be read when parsed statement shape, required fields, field meanings, `statement_metadata.accounts[]`, or extracted-record `account_id` relationships are unclear or inconsistent.
- `.agents/skills/shared/memory-access-rules.md` MUST be read before using, rejecting, correcting, or proposing governed memory hints for category, account, transfer, duplicate, naming, clarification, or import-source behavior
- `.agents/skills/auto-bean-categorize/references/categorize-artifact-rules.md` MUST be read before creating or updating a user-facing categorize artifact.

Workflow:

1. Confirm the assigned scope:
   - handle only the assigned parsed/intermediate statement, status entry, and shared artifact prefix
   - do not scan for other parsed files or raw statements
   - do not ask for commit, push, or final import approval
2. Inspect this statement and ledger context:
   - read the assigned parsed evidence, current status entry, and supplied memory hints
   - use `$auto-bean-query` for ledger reads, account discovery, register inspection, balances, date-bounded activity, duplicate exploration, transaction existence, and account constraints
   - do not approximate those reads by grepping ledger transactions when `$auto-bean-query` can answer them
3. Create or open the working categorize artifact:
   - read `.agents/skills/auto-bean-categorize/references/categorize-artifact-rules.md`
   - create `.auto-bean/artifacts/categorize/<artifact_prefix>--categorize.md` early as the working review surface for this statement
   - if an artifact already exists, use it as the working review surface and preserve any clearly labeled `Import Batch Cross-Statement Review` section
   - keep collecting safe progress in the artifact while working
4. Categorize each transaction in the assigned parsed statement:
   - use current parsed facts plus relevant `.auto-bean/memory/MEMORY.md` context and governed workflow memory hints from `.auto-bean/memory/category_mappings.json`.
   - treat parsed `account_owner` and `account_names` as statement evidence for selecting account mappings, transfer context, and memory applicability; do not treat them as ledger account names unless a current ledger check or approved mapping supports that
   - if a memory-derived suggestion materially affects a posting account, category, transfer classification, duplicate decision, or user question, read `.agents/skills/shared/memory-access-rules.md` even when the suggestion was supplied by `$auto-bean-import`
   - if memory matches under the shared strong-evidence threshold, record the matched memory path, record identity or stable summary, matched transaction facts, and resulting category/account suggestion
   - if no reliable memory matches, suggest likely category/account with evidence, confidence, and alternatives
   - use web search when an unknown merchant, processor label, local business, charity, school, subscription, agency, healthcare provider, travel vendor, or venue needs public evidence to identify its business type
   - build searches from cleaned payee text plus likely location inferred from surrounding same-statement transactions, currencies, addresses, station/airport codes, language, or account-owner context; start local and broaden only if needed
   - prefer official, directory, map, regulator, charity, school, healthcare, app-store, or reputable local sources; separate the merchant from processors, marketplaces, venues, platforms, or parent companies
   - never use web search alone for transfers, duplicates, account ownership, or ledger account existence; never browse account portals or expose private financial context
   - record web-assisted suggestions with compact query/location/source rationale; require user input when results are weak, conflicting, stale, generic, or location-mismatched
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
   - apply the shared fail-closed invariant with `categorize_blocked` when a finding cannot be safely classified or resolved; do not guess, auto-net, auto-merge, silently drop, or rewrite candidate transactions
6. Handle clarification needs:
   - set `user_input_required: true` when account/category choice, transfer intent, duplicate suspicion, source-specific meaning, or categorization remains materially ambiguous
   - follow the shared question-handling rules; when invoked by `$auto-bean-import`, never ask the user directly, and return only persisted question ids, the categorize artifact path, and operational blocker flags so `$auto-bean-import` can broker the question in the main thread
7. Update only this statement's status:
   - require the assigned statement to be at `categorize_ready` before categorization work starts
   - set `categorize_blocked` when required categorization, reconciliation, duplicate, transfer, or source-interpretation input is unresolved
   - set `categorize_review` after categorization, reconciliation, and deduplication work is persisted, with any user-input needs recorded in the categorize artifact

   - allowed status updates from this stage are `categorize_blocked` and `categorize_review`; `$auto-bean-import` advances later statuses after review, posting, validation, and approval
   - refresh the matching entry in `statements/import-status.yml`; do not create a second workflow-tracking file, and do not copy warning, question, or answer payloads into the status entry
8. Return control to `$auto-bean-import`:
   - assigned parsed/intermediate artifact path
   - categorize artifact path, including whether it needs user completion
   - short summary of what was categorized, reconciled, deduplicated, or blocked
   - categorization results and memory attribution
   - suggested transaction posting inputs for `$auto-bean-import` to pass to `$auto-bean-write` after user input is resolved
   - status changes and compact pending-question metadata for this artifact, following the shared artifact boundary
   - reconciliation/deduplication findings with suggested actions
   - every persisted pending user question id and the artifact path where the full question is recorded
   - `memory_md_suggestions`: concise suggested `.auto-bean/memory/MEMORY.md` updates for the main thread, or `[]` when none were found

Guardrails:

- Follow the shared workflow rules for ownership boundaries, status management, question handling, sub-agent handoff, compact returns, and memory use.
- Do not edit `.auto-bean/memory/MEMORY.md` when running as a sub-agent.
- Do not bypass clarification with a best guess when ambiguity is material.
- Do not erase import-batch cross-statement review notes when resuming or updating a categorize artifact.
