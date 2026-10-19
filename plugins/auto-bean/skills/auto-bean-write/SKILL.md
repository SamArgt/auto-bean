---
name: auto-bean-write
description: Draft or correct Beancount transactions from evidence. Use for ledger entries, explicit postings, transaction validation, and clarification of ambiguous transaction facts.
---

Read [plugin execution](../../references/plugin-execution.md), [workflow rules](../../references/workflow-rules.md), [candidate review](../../references/candidate-review.md), and relevant workspace `.auto-bean/memory/MEMORY.md` context. Use [ledger semantics](../../references/beancount-syntax-and-best-practices.md) for unfamiliar directives/costs; consult official Beancount docs through Context7 when semantics remain unclear.

## Evidence and scope

Identify direct versus import invocation. Inspect the ledger include graph, target accounts' `open`/`close` directives and currencies, nearby entries, and existing metadata/file conventions. Use `$auto-bean:auto-bean-query` for ledger facts. Evidence may be explicit user facts, a correction request, or reviewed source artifacts. Do not invent payees, currencies, amounts, account identity, or transfer intent.

For imports, require parsed, process, categorize, and import artifact paths plus reviewed posting dispositions and the assigned posting owner. Missing context blocks the write. Read [parsed inspection](../../references/parsed-statement-jq-reading.md) and validate evidence using [state validation](../../references/state-validation.md). Read [memory rules](../../references/memory-access-rules.md) when hints influence decisions; match them against current evidence.

## Draft and resume

1. Capture existing user changes and target before hashes under candidate-review rules. Only one ledger writer may run. Check existing postings for the candidate's provenance before resuming an interrupted write.
2. Resolve missing date, payee/narration, accounts, amount/currency, duplicate/transfer intent, and balancing rationale before drafting affected entries. Direct use asks and waits; import workers persist questions in the owning import/categorize artifact and return IDs to import, never ask the user themselves.
3. Use explicit balanced postings and clear statement payees/narration, preserving the ledger's style. Keep distinct economic purchases separate. Default supporting directives are minimal required `open` and narrowly justified `balance` assertions. Respect closed accounts and currency restrictions. Include-file reorganization, new commodities, options, prices, or unrelated cleanup need an explicitly authorized owning workflow.
4. Preserve imported `source`, `source_fingerprint`, `account_id`, and `record_id`. Existing corrections retain provenance. Direct facts without external IDs use `source: "user-provided"` and a unique disclosed `manual-` record ID. IDs refer to source rows, not parse runs. A reviewed paired transfer is written once by its assigned owner, retaining both source-record references as posting metadata or explicit companion metadata; its non-owner links to that entry. Reviewed duplicates link to existing entries and are not posted again. Held records are never posted.
5. Confirm import document references resolve to raw evidence. Reuse the narrowest existing included file, then draft only the assigned candidate. Do not silently net, merge, or drop records.
6. Run `auto_bean bean-check ledger.beancount`. On failure, preserve the visible draft, report the exact failure and smallest repair, and block further ledger mutations. Record after hashes and the focused diff on success.
7. Present evidence, changed hunks/files, assumptions, reconciliation, and validation directly in conversation. Explicit approval is bound to that candidate's current hashes and successful revalidation. Apply candidate-review rules for rejection or changed/interrupted drafts. Do not commit or push without authorization.

Import workers return changed files, before/after hashes, validation, questions/blockers, provenance/dispositions, and memory suggestions using the shared compact schema. Return proposed `write_blocked` or `final_review` only; import alone updates status and accepts statements. Direct sessions may update global workspace memory; workflow JSON learning belongs to `$auto-bean:auto-bean-memory`.
