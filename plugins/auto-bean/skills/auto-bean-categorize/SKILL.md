---
name: auto-bean-categorize
description: Categorize parsed statements in a group assigned by auto-bean-import. Suggest categories and explicit postings from evidence, advisory memory and merchant research; return per-statement reconciliation findings and required input for import review.
---

Read [common guidance](../../references/common.md) and the import contract's [state](../../references/import-review.md#state-and-validation). Use [bounded inspection](../../references/import-review.md#reading-evidence) for large documents and the [parsed example](../../references/parsed-group.example.json) when fields are unclear.

## Scope and proposals

Work on the group assigned by Import, as a worker or serial stage. Read its JSON, status, session and supplied reconciliation context/answers. Handle only complete source sections released by Import, starting at `categorize_ready` or resuming as directed. Continue ready members while holding blocked members and linked transfers. Return per-source findings and one group status proposal; any unresolved member keeps the group blocked. Do not discover statements, edit shared status or memory, mutate the ledger, or request approval/commit/push. Return questions to the Import stage, which owns user interaction.

Use `$auto-bean:auto-bean-query` for ledger accounts, constraints, registers, balances and transaction/duplicate checks. Source account names/owner evidence do not establish ledger mapping without a current check or approved mapping.

Within the relevant `statements[]` source section, edit each `extracted_records[].review` directly according to the [statement schema](../../references/schemas/parsed-statement.schema.json). Persist explicit split postings, rationale, findings, disposition and source links; preserve answers and extracted facts. Ambiguity uses `state: needs_input`, rationale and optional suggestions beside the record. When a memory hint materially influenced a decision, identify it with the supporting or contradicting evidence in that decision’s rationale.

## Categorization

- Compare current facts with workspace context and `.auto-bean/memory/category_mappings.json`. Without a reliable match, give evidence-backed alternatives and explain uncertainty.
- Research unknown merchants or processor labels when public evidence can establish business type. Search cleaned payee text plus likely location from same-statement transactions, currencies, addresses, station/airport codes, language or owner context. Start local, then broaden without exposing private financial context or browsing account portals.
- Prefer official sites, directories/maps, regulators, charity/school/healthcare sources, app stores or reputable local sources. Distinguish merchants from processors, marketplaces, platforms and parent companies. Web evidence alone cannot establish transfer intent, duplicates, ownership or ledger account existence.
- Mark required input when a posting choice remains materially ambiguous or research is weak, conflicting, stale, generic or location-mismatched. Continue independent safe work without guessing.

## Reconciliation and deduplication

Read `.auto-bean/memory/transfer_detection.json` for transfer review and `deduplication_decisions.json` for duplicate review. Compare the assigned evidence with queried accepted ledger history and supplied parsed rows from this session; do not scan other statements independently.

Prefer exact amounts/currencies and imported IDs, links or stable metadata over narration similarity. Compare timing, institution/account identity, references, payees, posting accounts and cash-movement signs. Transfers need opposite movements, nearby dates and compatible ownership/account context. Recurring merchant/amount similarity alone does not prove duplication.

Use these optional findings with concrete rationale and links:

| Finding | Meaning |
| --- | --- |
| `likely_transfer` | Evidence supports reviewing both sides together. |
| `possible_future_transfer` | Transfer-like evidence lacks a matching existing/supplied counterpart. |
| `possible_duplicate` | A row may repeat ledger history or another supplied source. |
| `unbalanced` | Evidence cannot support balanced posting inputs. |
| `currency_risk` | Proposed postings conflict with allowed account currencies. |

Every record needs `post`, `existing_duplicate`, `paired_transfer` or `hold`. Existing duplicates identify their canonical transaction under the state contract. Import resolves cross-statement decisions and assigns one transfer owner; never post both source sides independently. Supply explicit balanced posting inputs for Write, even where an amount could be inferred. Account constraints and nearby balance assertions can support currency, missing-entry and duplicate findings.

Do not auto-net, merge, silently drop or rewrite transactions to resolve ambiguity. Hold uncertain records and return the required decision to Import.

## Return to import

Return affected source/record IDs, the group parsed path, findings and proposed next status under the [ownership rules](../../references/common.md#ownership). Detailed payloads remain in inline review; Memory later derives reusable rules from accepted decisions. An unusual cross-workflow preference may be returned as an exact Markdown patch suggestion with evidence for the main thread, without adding a tracking field.

Propose only `categorize_blocked` for unresolved input/repair, with `user_input_required: true` where relevant, or `categorize_review` when categorization, reconciliation and deduplication are persisted and blockers resolved. Saved answers remain blocking until checked and resolved; preserve the current answer beside its decision. Import alone applies status and releases posting inputs after required input and batch review are complete.
