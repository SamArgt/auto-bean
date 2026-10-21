---
name: auto-bean-write
description: Draft or correct Beancount transactions from evidence. Use for ledger entries, explicit postings, transaction validation, and clarification of ambiguous transaction facts.
---

Read [common guidance](../../references/common.md) once. Imports use the [import data contract](../../references/import-review.md#transaction-dispositions). Consult [ledger semantics](../../references/ledger-reference.md#directives) for unfamiliar directives or costs.

## Evidence and drafting

1. Inspect the include graph, account dates/currencies, nearby entries and metadata conventions. Use `$auto-bean:auto-bean-query` for ledger facts. Do not invent payees, amounts, currencies, ownership or transfer intent.
2. Resolve missing facts and balancing rationale before writing. Direct use asks the user; import workers return affected account/record IDs and supported suggestions to Import. Import input is the complete current group parsed JSON and its source sections, resolved mappings/postings, assigned transfer owner and current explicit approval. Read bounded excerpts when needed.
3. Use explicit balanced postings and preserve distinct purchases and ledger style. For new imported entries, narration equals the extracted description and an extracted payee is retained. Shared transfers use the posting owner’s description/payee; within one source, the lexicographically first linked record ID owns the posting. Supporting directives are limited to reviewed required account openings, source-supported opening transactions, document links and justified balance assertions. Unrelated cleanup, options, new commodities and prices belong to their authorized workflow.
4. Preserve imported `source`, `source_fingerprint`, `account_id` and `record_id`. A paired transfer is written once with both source identities; its non-owner links to that transaction. Reviewed duplicates identify existing entries and may retain their existing narration, but their date, payee when present, exact postings and source-account movement must match. Held records are never posted. Direct facts without external IDs use `source: "user-provided"` and a unique disclosed `manual-` record ID.
5. Before adding an entry, check existing provenance. An identical reviewed entry is already written; a conflicting or duplicate identity needs repair. Never blindly append all parsed rows on resume.

## Import writing and validation

For imports, reread the current ledger and parsed decisions, confirm explicit approval of that content in conversation or the panel, then edit the narrowest included ledger files directly. Follow common ownership and serialization rules. The parsed postings are the sole input; do not create a second transaction file, approval record or execution journal. If the approved content has changed materially, return for renewed review.

After the assigned statement or linked group has been written, run [shared validation](../../references/common.md#validation) with `--session <id> --stage written`. Return its group and per-source reports and any session-wide error to Import. Only a group whose every source passes written validation can become `done`. The check covers actual rows, postings, provenance, supporting directives and available balances. Never hand-author its result. Affected failures block dependent writes until repaired. Interrupted work resumes from actual provenance and current file contents, never a whole-file rollback.

Return changed paths, validation results, any required repair and eligible learning evidence under the [ownership rules](../../references/common.md#ownership). Import alone advances status to `done` and coordinates import-memory updates. For standalone writes, route eligible learning to `$auto-bean:auto-bean-memory`; only the main thread edits workspace `MEMORY.md`.

## Direct review

Use this procedure for standalone transaction edits. Prices and Init also use it for their own price or setup changes; they retain ownership of those edits. Present review in conversation without a separate mutation artifact.

1. Inspect relevant staged, unstaged and untracked changes. Retain target paths, before SHA-256 hashes (`null` for absent files), exact proposed hunks and recoverable original contents in the execution context. Git HEAD alone does not preserve user changes. Validate the baseline ledger; existing errors need a bounded repair decision before drafting.
2. With one ledger writer, recheck before hashes, draft the narrow authorized changes, run `auto_bean validate --workspace "$AUTO_BEAN_WORKSPACE"`, inspect the diff and retain after hashes. A failed draft blocks dependent writes until resolved. Disclose unapproved drafts and exclude them when identifying accepted balances or duplicates.
3. Present evidence, exact changes, validation, reconciliation and unresolved risks. Approval covers those hunks and after hashes; recheck them and validation before acceptance. Changed drafts require renewed review; unchanged approved drafts need no repeated permission. Commit only authorized paths/hunks when requested, never the whole workspace; push requires authorization.
4. On rejection, remove only the draft's hunks when current contents still match, then validate what remains. Preserve unrelated user edits. Missing baselines or overlapping changes require conflict resolution; never blindly reset, stash or restore whole files. Rejection is not completion.

On resume, inspect the existing diff and source/account/record provenance before continuing or repairing the same draft. Never append it twice. Ask before undoing changes whose original hunks or ownership cannot be recovered.
