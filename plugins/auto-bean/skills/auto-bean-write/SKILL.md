---
name: auto-bean-write
description: Draft or correct Beancount transactions from evidence. Use for ledger entries, explicit postings, transaction validation, and clarification of ambiguous transaction facts.
---

Read [common guidance](../../references/common.md) once. Direct requests use [conversation review](../../references/ledger-reference.md#direct-review); imports use the [import data contract](../../references/import-review.md#transaction-dispositions). Consult [ledger semantics](../../references/ledger-reference.md#directives) for unfamiliar directives or costs.

## Evidence and drafting

1. Inspect the include graph, account dates/currencies, nearby entries and metadata conventions. Use `$auto-bean:auto-bean-query` for ledger facts. Do not invent payees, amounts, currencies, ownership or transfer intent.
2. Resolve missing facts and balancing rationale before writing. Direct use asks the user; import workers return affected account/record IDs and supported suggestions to Import. Import input is the complete current parsed document, resolved mappings/postings, assigned transfer owner and current explicit approval. Read bounded excerpts when needed.
3. Use explicit balanced postings and preserve distinct purchases and ledger style. For new imported entries, narration equals the extracted description and an extracted payee is retained. Shared transfers use the posting owner’s description/payee; within one source, the lexicographically first linked record ID owns the posting. Supporting directives are limited to reviewed required account openings, source-supported opening transactions, document links and justified balance assertions. Unrelated cleanup, options, new commodities and prices belong to their authorized workflow.
4. Preserve imported `source`, `source_fingerprint`, `account_id` and `record_id`. A paired transfer is written once with both source identities; its non-owner links to that transaction. Reviewed duplicates identify existing entries and may retain their existing narration, but their date, payee when present, exact postings and source-account movement must match. Held records are never posted. Direct facts without external IDs use `source: "user-provided"` and a unique disclosed `manual-` record ID.
5. Before adding an entry, check existing provenance. An identical reviewed entry is already written; a conflicting or duplicate identity needs repair. Never blindly append all parsed rows on resume.

## Direct writing and validation

For imports, reread the current ledger and parsed decisions, confirm explicit approval of that content in conversation or the panel, then edit the narrowest included ledger files directly. Follow common ownership and serialization rules. The parsed postings are the sole input; do not create a second transaction file, approval record or execution journal. If the approved content has changed materially, return for renewed review.

Run [shared validation](../../references/common.md#validation) with `--session <id> --stage written`. It independently checks the actual rows, postings, provenance, supporting directives and available balances. Never hand-author its result. Return concrete row/account errors if validation fails; dependent writes wait for repair. Interrupted work resumes from actual provenance and current file contents, never a whole-file rollback.

Direct requests retain the conversation-review procedure for drafting, approval, rejection and recovery. No commit or push without authorization.

Return changed paths, validation result and any required repair under the [ownership rules](../../references/common.md#ownership). Import alone advances status to `done`. Route eligible reusable learning to `$auto-bean:auto-bean-memory`; only the main thread edits workspace `MEMORY.md`.
