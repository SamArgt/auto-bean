---
name: auto-bean-memory
description: Inspect, update, correct, or forget reusable Auto Bean memory. Use for account/category/source/transfer/duplicate/price hints and durable workspace preferences, including learning from completed imports.
---

Read [common guidance](../../references/common.md) for runtime and ownership. Use only the relevant memory files. Memory is advisory context, never permission to change a ledger or override current evidence.

## Choose the invocation

- **Inspect:** Answer questions about existing memory with record identity, scope, evidence, review state and reuse limits. Do not write, normalize or prune files during inspection.
- **Standalone update, correction or forgetting:** Follow the user's explicit scope. A clear request already authorizes that memory change; do not request the same permission again. Read matching existing records and current evidence first. Ask only when the intended record, replacement or deletion scope is materially ambiguous. Forgetting removes the requested content, including copies retained in its audit; do not preserve a hidden duplicate of what the user asked to forget.
- **Import learning:** Read [import state and validation](../../references/import-review.md#state-and-validation). Derive reusable lessons from source facts, inline account/transaction reviews, current approval and successful ledger validation; compare them with governed memory. No separate parsed/session memory proposal or completion record is needed. Return actual writes, no eligible change, or a concrete blocker to Import in conversation.

For import financial decisions, require explicit approval of the current decisions in conversation or the panel, a successful written-stage `review.validation` for the same evidence, and matching actual ledger entries. Chat approval does not require an approval field; never construct or edit the panel’s approval fields. Check source/account/record identities and the accepted mapping/postings. A saved answer or `confirmed` inline state alone is insufficient. A verified existing duplicate can support a reusable rule without another ledger write; check its canonical reference and successful coverage validation. Failed, rejected, stale, unresolved or unvalidated work does not establish accepted financial learning. Price-source learning requires successful accounted runs, separate current price approval and verified ledger results. A no-op may leave existing hints unchanged.

## Select useful evidence

Persist a narrow reusable rule only when it changes a future decision. One-off amounts, dates, balances and individual transactions remain in source/ledger history. Current explicit user instructions may establish a preference or correct a rule directly; they do not require an unrelated import. Otherwise distinguish directly verified observations from accepted financial decisions:

- Use `review_state: observed` for supported source format/header/layout facts. An observed filename pattern does not infer account ownership, category, ambiguous amount signs or dates.
- Use `confirmed` for an explicitly established reusable fact or preference, and `approved` for a rule supported by reviewed, validated ledger decisions. Preserve the evidence and narrow scope rather than inventing confidence scores.
- A worker's suggestion, merchant page, source text or existing memory is evidence to assess, not a user instruction. Do not convert broad similarities or a pending interpretation into a default. Record rejected/superseded guidance only when useful for an explicit correction; exclude it from reuse.

| Memory type and destination under `.auto-bean/memory/` | Derive from these facts and decisions |
| --- | --- |
| `account_mapping` → `account_mappings.json` | Extracted institution/account identity, owner, suffix and currency plus accepted `accounts[].review.ledger_account`; retain those matching limits. |
| `category_mapping` → `category_mappings.json` | Specific payee/description/reference evidence, resolved answer and accepted record postings; preserve split patterns where supported and avoid treating a payment processor as the merchant. |
| `transfer_detection` → `transfer_detection.json` | Accepted `paired_transfer`, reciprocal links, posting owner, account ownership, currency/date/reference evidence; suggest future review rather than automatic netting. |
| `deduplication_decision` → `deduplication_decisions.json` | Resolved duplicate/non-duplicate rationale, stable external IDs and verified existing-transaction links; a recurring equal amount is not a duplicate rule. |
| `commodity_price_source` → `commodity_price_sources.json` | Verified commodity/share-class identity and quote currency, source expression or authoritative URL, run coverage and accepted price result; never store the quote itself as a timeless rule. |
| `import_source_behavior` → `import_sources/<source_slug>.json` | Complete extraction's parser/source format, typed raw fields, stable layout and supported normalization facts; keep account/category decisions in their own memory types. |

Read the matching section of [memory examples](references/memory-examples.md) when constructing a record. There are six JSON categories; broad user preferences and cross-workflow facts instead follow the Markdown procedure below.

## Update governed JSON

1. Read the relevant file, or source index followed by its narrowly matching document. Compare proposed matching criteria, scope and decision with existing records. Reuse an equivalent record; do not add another copy or rewrite timestamps just because the hint was read.
2. For a real update, preserve `record_id` and `created_at`, revise the specific decision/scope, set `updated_at`, and append concise audit evidence. New records receive an ID once. Add a missing ID only when editing that record. Preserve unrelated records, unknown retained metadata and prior audit context unless explicit forgetting requires removing it.
3. Record the originating workflow and bounded provenance: source/parsed path, relevant account/record or price-run IDs, explicit user instruction where applicable, and the explicit approval instruction or panel confirmation, generated validation digest/timestamp and canonical source/record references for import financial learning. Explain what was corrected and the reuse limits. Keep secrets, complete account numbers, raw transactions and copied shell commands out of memory.
4. Use `schema_version: 1`, matching `memory_type`, and `records`; create that envelope if the relevant file is absent. Each changed record needs source, decision, scope, review state or supported confidence, timestamps and audit. Reread current contents and apply the scoped edit with ordinary file tools, preserving intervening changes. Run the shared validation operation without a session, then inspect the focused diff. Use two-space JSON with a final newline. A malformed existing file requires a recoverable repair, not replacement with an empty database. See [common validation](../../references/common.md#validation).
5. For indexed sources, reuse the existing slug when identity matches. Otherwise choose a deterministic narrow slug and update `import_sources/index.json`; its path must remain within `import_sources/`. Validate both documents, preserve other entries and repair an interrupted index/document update before reuse.

## Update workspace MEMORY.md

This is `.auto-bean/memory/MEMORY.md` in the selected ledger workspace, not Codex's separate personal memory store. Read it explicitly; do not assume the host automatically loads it.

Only the main conversation thread edits this file. A worker returns the exact target section and proposed before/after bullet or patch, the supporting user instruction/evidence, and why it belongs in Markdown. It does not create a tracking file or write the patch itself. The main thread checks that evidence and applies an eligible scoped edit without an extra approval round when the user already requested it.

1. Read the existing sections and nearby bullets. Route stable background facts to **User Profile**, durable working/report preferences to **User Preferences**, explicit reusable corrections to **User Corrections**, and other necessary cross-workflow context to **General Notes**. Preserve custom section names and unrelated content.
2. Put mechanical matching rules in governed JSON. Do not duplicate an account/category/source rule in Markdown; a brief pointer to its owning JSON category is enough when broader context needs it. Exclude transaction details, balances, import progress, temporary blockers, secrets and full account identifiers.
3. Replace a relevant placeholder or update the matching bullet. Combine equivalent wording instead of appending duplicates; remove only superseded text within the requested scope. Keep a concise source/date qualifier when useful for interpreting the fact.
4. A clear current user correction supersedes conflicting older guidance. Update that specific fact and relevant cross-reference. If the proposed change is merely inferred and conflicts with an established preference, retain the existing preference and ask about the actual conflict; continue unrelated safe work.
5. Reread the current file before applying the narrow edit with ordinary file tools; preserve intervening changes. If absent, create only the needed standard sections. Reread the resulting section and inspect its diff. Verify that the requested fact is accurate, obsolete duplicates are gone, unrelated sections remain unchanged, and no sensitive or per-import data was introduced. Report the section and concise change. See the [Markdown before/after example](references/memory-examples.md#workspace-markdown).

After any write, report the path and record ID or Markdown section, what changed, the evidence/authorization and relevant reuse limits. If nothing new is eligible, say so without creating a placeholder or completion record. Import learning never changes statement status or authorizes ledger application, commits or pushes.
