---
name: auto-bean-memory
description: Inspect, update, correct, or forget reusable Auto Bean memory. Use for account/category/source/transfer/duplicate/price hints and durable workspace preferences, including learning from completed imports.
---

Read [common guidance](../../references/common.md) for runtime and ownership. Use only the relevant memory files. Memory is advisory context, never permission to change a ledger or override current evidence.

## Choose the invocation

- **Inspect:** Report record identity, scope, evidence, review state and reuse limits. Do not edit files.
- **Update, correct or forget:** The user's clear request authorizes that scoped change. Read matching records and current evidence; clarify only ambiguous targets or changes. Forgetting also removes copies in the record's audit.
- **Import learning:** Read supplied session/group JSON and compare eligible lessons with existing memory. Use [import state](../../references/import-review.md#state-and-validation) for field meanings. Return changes or blockers to Import without a separate memory artifact.

For import financial learning, require current explicit approval, passed written validation for the same evidence, and matching ledger entries with source/account/record identities. A saved answer or `confirmed` state alone is insufficient. Existing duplicates need a verified canonical reference and passed coverage validation, not another write. Follow common approval ownership; never construct panel approval fields.

Price-source learning needs verified commodity/share-class identity, quote currency, an accounted successful run and matching ledger prices. New price writes also need separate current approval. An entirely redundant run may establish a narrow source hint without another approval when its exact directives already exist in accepted ledger history and written validation passes. Do not treat unapproved drafts as accepted prices. Zero-job no-ops establish no new source evidence. Failed, rejected, stale or unresolved work does not establish accepted financial learning.

## Select useful evidence

Persist only narrow rules that change future decisions. Keep one-off transactions, amounts, dates and balances in source/ledger history. Explicit user instructions can establish preferences or correct rules without an import. Otherwise distinguish observations from accepted financial decisions:

- `observed`: verified format/header/layout facts, never inferred ownership, category, ambiguous signs or dates.
- `confirmed`: explicitly established reusable facts or preferences. `approved`: rules supported by reviewed, validated ledger decisions. Preserve evidence and scope; do not invent confidence scores.
- Apply common evidence trust rules. Broad similarities and pending interpretations are not defaults. Retain rejected/superseded guidance only to explain a correction; exclude it from reuse.

| Memory type and destination under `.auto-bean/memory/` | Derive from these facts and decisions |
| --- | --- |
| `account_mapping` → `account_mappings.json` | Extracted institution/account identity, owner, suffix and currency plus accepted `accounts[].review.ledger_account`; retain those matching limits. |
| `category_mapping` → `category_mappings.json` | Specific payee/description/reference evidence, resolved answer and accepted record postings; preserve split patterns where supported and avoid treating a payment processor as the merchant. |
| `transfer_detection` → `transfer_detection.json` | Accepted `paired_transfer`, reciprocal links, posting owner, account ownership, currency/date/reference evidence; suggest future review rather than automatic netting. |
| `deduplication_decision` → `deduplication_decisions.json` | Resolved duplicate/non-duplicate rationale, stable external IDs and verified existing-transaction links; a recurring equal amount is not a duplicate rule. |
| `commodity_price_source` → `commodity_price_sources.json` | Verified commodity/share-class identity and quote currency, source expression or authoritative URL, run coverage and accepted price result; never store the quote itself as a timeless rule. |
| `import_source_behavior` → `import_sources/<source_slug>.json` | Complete extraction's parser/source format, typed raw fields, stable layout and supported normalization facts; keep account/category decisions in their own memory types. |

Read the matching [example](references/memory-examples.md) when constructing an unfamiliar record. Broad preferences and cross-workflow facts use Markdown instead.

## Update governed JSON

Use the [memory schema](../../references/schemas/memory.schema.json) for governed memory files and the source index.

1. Read matching records, using the source index first for extraction hints. Compare criteria, scope and decision. Reuse equivalent records without duplicating them or changing timestamps merely because they were read.
2. For updates, keep `record_id` and `created_at`, change only the affected decision/scope, set `updated_at` and append audit evidence. Assign an ID once to new records, or when editing a record without one. Preserve unrelated records, retained metadata and audit context except for explicit forgetting.
3. Record the workflow, bounded evidence paths and account/record or price-run IDs. For financial learning, include approval when required above, validation digest/timestamp and canonical ledger references. For a redundant price run, record the accepted-price evidence instead of inventing approval. Explain corrections and reuse limits. Exclude secrets, full account numbers, raw transactions and copied shell commands.
4. Use the schema's version-1 envelope and matching memory type. Each changed record needs source, decision, scope, review state or supported confidence, timestamps and audit. Apply scoped edits under common ownership rules. Validate without a session and inspect the diff. Use two-space JSON and a final newline. Repair malformed existing files recoverably; never replace them with an empty database.
5. Reuse an indexed source slug when identity matches; otherwise use a deterministic narrow slug. Update `import_sources/index.json` with a path inside `import_sources/`. Validate both documents and repair interrupted paired updates before reuse.

## Update workspace MEMORY.md

This is `.auto-bean/memory/MEMORY.md` in the selected ledger workspace, not Codex's separate personal memory store. Read it explicitly; do not assume the host automatically loads it.

Only the main thread edits this file. A worker returns the target section, before/after bullet or patch, supporting evidence and why it belongs in Markdown. The main thread applies eligible scoped edits under existing authorization; no tracking file or repeated permission is needed.

1. Read nearby bullets. Use **User Profile** for background, **User Preferences** for working/report preferences, **User Corrections** for reusable corrections and **General Notes** for other cross-workflow context. Preserve custom sections; create only needed sections when absent.
2. Keep mechanical matching rules in JSON; use a brief pointer if needed. Exclude transaction details, balances, progress, temporary blockers, secrets and full account identifiers.
3. Update matching bullets or placeholders, combine duplicates and remove only superseded text within scope. Add source/date qualifiers when useful. Explicit current corrections supersede older guidance; inferred conflicts require clarification while unrelated work continues.
4. Apply common scoped-edit rules, reread the result and inspect its diff. Verify the fact, removal of obsolete duplicates and preservation of unrelated content. See the [before/after example](references/memory-examples.md#workspace-markdown).

After any write, report the path and record ID or Markdown section, what changed, the evidence/authorization and relevant reuse limits. If nothing new is eligible, say so without creating a placeholder or completion record. Import learning never changes group status or authorizes ledger application, commits or pushes.
