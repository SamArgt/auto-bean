---
name: auto-bean-categorize
description: Categorize one parsed statement assigned by auto-bean-import. Suggest accounts and categories from current evidence, advisory memory, and merchant research; return reconciliation findings, questions, and explicit posting inputs for import review.
---

Read [plugin execution](../../references/plugin-execution.md), [workflow rules](../../references/workflow-rules.md), and workspace `.auto-bean/memory/MEMORY.md` before acting. Resolve packaged resources relative to this file and financial-data paths against the selected workspace.

Read [parsed-statement reading](../../references/parsed-statement-jq-reading.md) before inspecting large parsed JSON and [status reading](../../references/import-status-reading.md) before interpreting a large status index. Use [state validation](../../references/state-validation.md) before consuming parsed evidence; consult the [parsed example](../../references/parsed-statement-output.example.json) when fields or `statement_metadata.accounts[]`/record `account_id` relationships are unclear. Read [memory access rules](../../references/memory-access-rules.md) before using, rejecting, correcting, or proposing governed hints, including hints supplied by import.

## Scope and inputs

Handle only the statement assigned by `$auto-bean:auto-bean-import`: one parsed JSON file (or explicit Markdown handoff pointing to it), its `statements/import-status.yml` entry, shared raw-statement artifact prefix, and supplied memory, reconciliation context, or approved answers. Start categorization at `categorize_ready`; on an import-directed resume, preserve the existing artifact and answers.

Do not discover other statements, edit the shared status index, mutate ledger files, ask users directly, request final approval/commit/push, or edit `MEMORY.md`. Import brokers questions and owns batch review and later status advancement. Use `$auto-bean:auto-bean-query` for ledger accounts, constraints, registers, balances, date-bounded activity, and transaction/duplicate checks rather than approximating queryable facts by grepping transactions.

## Working artifact

Create `.auto-bean/artifacts/categorize/<artifact_prefix>--categorize.md` early, using the shared prefix, or update the existing artifact. Preserve any `Import Batch Cross-Statement Review` section appended by import. Keep safe progress and the audit trail even for trivial, unblocked statements.

Include source parsed/raw paths, statement/status id, artifact prefix, categorization results, explicit posting inputs, reconciliation/deduplication findings, pending/answered questions, warnings/blockers, and memory suggestions with attribution. Link evidence and stage-owned detail under shared privacy/ownership rules. For web-assisted suggestions, record query, inferred location, sources, rationale, confidence, and alternatives.

Make questions fillable by a non-technical user: stable ids, observed facts, suggestions, risks of guessing, choices, short account/category blanks, and “leave blank if unknown” guidance. Separate editable answers from facts and suggestions. A compact question can use:

```markdown
### Q1 — <transaction id>

Observed: <date, payee, amount/currency, evidence link>
Suggestion: <account/category, confidence, rationale>
Why input is needed: <remaining ambiguity and risk>
Choose one; leave blank if unknown.

- [ ] Use suggestion
- [ ] Use: ____________________
- [ ] Not sure / hold for now

Note: ____________________
```

## Categorization

- Inspect assigned parsed evidence, status, supplied context, and relevant ledger facts. Treat parsed `account_owner` and `account_names` as evidence for mapping applicability, not ledger account names without a current ledger check or approved mapping.
- Categorize each transaction using current facts, relevant `MEMORY.md` context, and `.auto-bean/memory/category_mappings.json`. Memory remains advisory under the shared strong-evidence threshold. Record matched memory path/record identity (or stable summary), matched facts, and resulting account/category suggestion. Without a reliable match, give evidence-backed suggestions, confidence, and alternatives.
- Research unknown merchants or ambiguous processor labels when public evidence can establish business type. Search cleaned payee text plus likely location from same-statement transactions, currencies, addresses, station/airport codes, language, or owner context; start local and broaden as needed without exposing private financial context or browsing account portals.
- Prefer official sites, directories/maps, regulators, charity/school/healthcare sources, app stores, or reputable local sources. Distinguish the merchant from processors, marketplaces, venues, platforms, and parent companies. Web evidence alone cannot establish transfers, duplicates, ownership, or ledger account existence.
- Persist a question when a posting choice remains materially ambiguous or research is weak, conflicting, stale, generic, or location-mismatched. Continue other safe work; do not turn uncertainty into a guessed posting.

## Reconciliation and deduplication

Load `.auto-bean/memory/transfer_detection.json` before transfer detection and `.auto-bean/memory/deduplication_decisions.json` before duplicate decisions. Compare this statement's parsed transactions and posting suggestions against queried ledger history and supplied candidates; do not scan other statements yourself.

Prefer exact amounts/currencies and imported ids, links, or stable metadata over narration similarity. Compare dates, institution/account identity, references, payees, posting accounts, and cash-movement signs. Transfers need opposite movements, nearby timing, and compatible ownership/account context. Compare duplicates against both ledger history and supplied same-run candidates; familiar recurring merchants/amounts alone do not prove duplication.

Use only these finding types, each with `finding_type`, `candidate_scope` (transaction/record refs), `summary`, and concrete `evidence`:

| Type | Meaning |
| --- | --- |
| `likely_transfer` | Both sides are present strongly enough to review together |
| `possible_future_transfer` | Transfer-like evidence without a matching existing/supplied counterpart; do not assume the match |
| `possible_duplicate` | Candidate may already exist in the ledger or be repeated in the run |
| `unbalanced` | Explicit evidence cannot support balanced posting inputs |
| `currency_risk` | Suggested account conflicts with allowed currencies, usually declared by `open` |

Give each record a proposed disposition (`post`, `existing_duplicate`, `paired_transfer`, or `hold`) with evidence and referenced transaction/paired record. Import resolves spanning candidates and assigns one transfer posting owner; this skill never posts both sides independently. Transactions must balance when posted. Produce explicit posting inputs for import to pass to `$auto-bean:auto-bean-write`, even where Beancount could infer an omitted amount. Use account constraints and nearby `balance` assertions as supporting evidence for currency, missing-entry, or duplicate risks.

When a finding cannot be safely classified/resolved, apply the shared fail-closed rule and propose `categorize_blocked`. Never auto-net, merge, silently drop, or rewrite candidate transactions to resolve ambiguity.

## Questions, status, and return

Persist full questions and deterministic progress in the categorize artifact. Return `user_input_required: true` for unresolved material account/category, transfer, duplicate, or source-interpretation choices. Return question ids, artifact path, and compact blockers to import; it records answers and resumes this stage when needed.

Return a proposed update for only the assigned status entry; import alone applies it: `categorize_blocked` for unresolved required input/repair; `categorize_review` once categorization, reconciliation, and deduplication are persisted and required blockers are resolved. Preserve question/answer history in the artifact. These are the only statuses this skill may propose; status stores pointers and compact flags, not detailed warnings/questions/answers. Do not create another tracking file.

Return the shared compact schema with assigned parsed/handoff path, categorize artifact path and completion needs, short work summary, status changes, categorization results and memory attribution, findings/suggested actions, and explicit posting inputs. Include every pending question id and its owning artifact path, eligible governed-memory suggestions, and `memory_md_suggestions` for main-thread review (or `[]`). Detailed review payloads stay in the artifact; import releases posting inputs only after required input and batch review are resolved.
