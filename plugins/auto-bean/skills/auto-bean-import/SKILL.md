---
name: auto-bean-import
description: Import statements from discovery through processing, account inspection, categorization, ledger writing, validation, and final user review. Use for new statements or resumed imports tracked in statements/raw/ and statements/import-status.yml.
---

Read [plugin execution](../../references/plugin-execution.md), [workflow rules](../../references/workflow-rules.md), and workspace `.auto-bean/memory/MEMORY.md`. Before status changes, read [status handling](../../references/import-status-reading.md) and [state validation](../../references/state-validation.md); before ledger edits, read [candidate review](../../references/candidate-review.md). Read [memory rules](../../references/memory-access-rules.md) when handling hints and the [status example](../../references/import-status.example.yml) when adding fields or repairing schema.

## Orchestration

Resume each statement from persisted status; completed statements require explicit rework, even if the source changed. Continue independent safe work while others wait, but hold a posting cohort when unresolved cross-statement evidence affects its transfer/duplicate decisions.

You alone merge worker status proposals into the latest index, preserve unrelated entries, and validate transitions against the previous snapshot. Processing/categorization may use parallel statement-scoped workers; serialize all ledger edits, including accounts, documents, and prices. Coordinate with other chats sharing the workspace. Use the shared handoff, question-brokering, compact-return, and candidate-recovery contracts; keep before/after hashes and approval evidence in existing import artifacts. Await dependent worker results; close process/categorize workers before downstream handoff.

## Import artifact

Create one `.auto-bean/artifacts/import/<artifact_prefix>--import.md` per raw statement before leaving `raw_ready`. Use a safe filename-stem slug, adding a parent slug or fingerprint suffix only for uniqueness; share it across stage artifacts. Do not combine statements unless explicitly requested.

Keep stable IDs and these sections when relevant:

| Section | Content |
| --- | --- |
| `# Import Decisions <artifact_prefix>` | `schema_version`, raw path/fingerprint, `artifact_prefix`, `created_at`, `updated_at` |
| `## Artifact References` | Source/parsed/stage/write/validation/memory paths and status key |
| `## Questions` | Import questions; stage-owned IDs, links, and resume decisions |
| `## First-Seen Account Decisions` | Proposals, evidence, targets, approval/write state, validation |
| `## Document Reference Decisions` | Account/date/raw path/target, duplicate check, decision/write state |
| `## Cross-Statement Review` | Paired artifact/record refs, evidence, decision, posting impact |
| `## Posting Decisions` | Write inputs/results, validation, blockers, candidate hashes, approval |
| `## Memory Attribution` | Used/rejected records, evidence checks, influenced decisions |
| `## Memory Candidates` | Provenance, originating artifact, review state, eligibility, deduplication |
| `## Ignored Or Rejected Inputs` | Unsafe/stale inputs, invalid suggestions, blockers/rejections |

Persist decisions before questions, handoffs, approval, memory writes, or `done`; refresh `updated_at`. Link stage-owned detail; keep operational counts/retries/transitions in status. Unsafe/conflicting paths, unwritable artifacts, or unresolved status/artifact disagreements block the statement under shared rules.

## 1. Discovery and processing

- Inspect Git status and the status index; fingerprint PDF/CSV/XLSX/XLS inputs. New entries start at `raw_ready`; restart changed or explicitly reprocessable inputs only under the status/rework rules.
- Read the import-source memory index first; select narrowly matching source behavior and retain evidence/reuse attribution.
- Assign each eligible `raw_ready` source to `$auto-bean:auto-bean-process` with its import artifact, expected parsed path, retry context, and selected hints. Accept only `process_blocked`, `process_review`, or `account_review` proposals; validate returned evidence before account decisions.
- Broker process questions/warnings. Record evidence-changing answers in the process artifact and linked resume decisions in import. Resume processing when normalization/regeneration is needed; resolved reviews advance to `account_review`, unresolved work retains its process state.

## 2. Accounts and balances

- At `account_review`/`account_blocked`, use `$auto-bean:auto-bean-query` and current source/account-mapping evidence to classify accounts as `existing_account`, `first_seen_candidate`, or `blocked_inference`.
- Infer first-seen institution-owned balance-sheet accounts/opening balances only for banking, credit cards, loans, cash, or investments, using strong current evidence. Present exact minimal directives, targets, evidence, and rationale; obtain approval/correction before writing. Prefer `beancount/accounts.beancount` and `beancount/opening-balances.beancount`.
- Propose one `YYYY-MM-DD document <ledger-account> "<raw-statement-path>"` per matched parsed account, dated to period end. Deduplicate by date/account/raw path, follow existing placement, and encode the path relative to the target ledger file. Include proposals in the import approval package; that approval covers them unless changed/rejected. Uncertain identity, currency, date, safe target, duplicate risk, or approval keeps `account_blocked`.
- Write only approved opening structure/document references/minimal supporting directives; validate with `auto_bean bean-check ledger.beancount`, then enter `balance_review`. Query opening balances and show mismatches/remediation choices; unresolved or untrustworthy checks remain `balance_blocked`. Resolved decisions and validated edits reach `categorize_ready`.
- Use beginning-of-day semantics for opening queries/assertions; end-of-day closing balances use the next calendar day. Check commodities separately. For transaction exports without periods, obtain the approved coverage/document date rather than inferring it from first/last rows. Missing reported balances are `not_available`, with rationale and approved account/date interpretation; use row-count/provenance checks instead, never invented balances.

## 3. Categorization and batch review

- Assign `categorize_ready` inputs to `$auto-bean:auto-bean-categorize`; accept `categorize_review`/`categorize_blocked` proposals. Broker questions through their owning artifacts and resume unfinished work before advancing.
- Review batch artifacts/posting inputs, including blocked statements, for transfers and duplicates against existing ledger activity via `$auto-bean:auto-bean-query`. Compare amount/currency, nearby dates, descriptions/references, fees, FX legs, and account pairs; do not silently drop, net, or deduplicate candidates.
- Add `Import Batch Cross-Statement Review` to affected categorize artifacts and linked paired-record decisions to import artifacts. Release only reviewed statements with resolved batch dependencies to `write_ready`.
- Give every record a disposition: `post`, `existing_duplicate`, `paired_transfer`, or `hold`. A paired transfer has one posting owner and one economic transaction retaining both source-record references; its non-owner links to that entry. Keep approved fees/FX legs explicit.

## 4. Writing and final approval

- Invoke `$auto-bean:auto-bean-write` serially for `write_ready` statements with parsed/process/categorize/import context. Record its mutation/validation return; broker questions and retain `write_blocked` for unresolved facts, repair, or failed validation. Apply shared resume/rejection rules; an unresolved partial/invalid candidate blocks later ledger writes.
- Written, validated transactions enter `final_review`. Query reported closing balances using the boundary rules above and reconcile artifact/status pointers; surface discrepancies before approval. Record unavailable export checks explicitly.
- Present per-statement changes, evidence/provenance, decisions, risks, validation, and reconciliation directly in conversation. Recheck candidate hashes/validation before acceptance; only explicit approval of that exact result permits `done`. Otherwise retain review/blocked state. Close write workers after their statements reach `done`; commit/push readiness remains import-owned under shared authorization rules.

## 5. Price epilogue

After statement writes and current review decisions, invoke `$auto-bean:auto-bean-prices` once before memory handoff; also resume prior price follow-ups. Skip fetching only when neither new writes nor pending follow-ups exist.

Supply changed files, account/commodity hints, validation, and artifact paths. Update held/import-touched commodities with one explicit dated snapshot without `--update`; historical backfill requires a separate request. Broker source questions and require terminal fetch completion with reconciled jobs. Running sessions or empty initial output are incomplete.

Report the price artifact/mode, terminal state/exit/duration, dry-run jobs, emitted/redundant/ignored counts, sanitized stderr, changed/skipped files and commodities, and validation. Obtain separate approval for later price edits; retain blockers/pending approval in the price artifact without moving `done` backward. Pass results and eligible source-memory suggestions onward.

## 6. Memory and completion

Invoke `$auto-bean:auto-bean-memory` once with consolidated eligible suggestions, provenance, artifact links, and current review state. Unresolved decisions cannot become durable learning or bypass statement gates. Review global `MEMORY.md` suggestions in the main thread.

Check status/artifact agreement and persisted decisions/questions/results before summarizing statement outcomes, ledger/status changes, validation, price/memory results, and remaining actions.

## Final status block

End every user-facing import response with this block and no text afterward:

```markdown
---

## Import Status: <label>

**Summary:** <concise outcome with counts/paths when useful.>
**Next Step:** <one user action, or "None." when Complete.>
```

Choose the label for the most important remaining action:

| Label | Condition |
| --- | --- |
| `Needs Your Input` | Unresolved source/account/balance/category/write questions |
| `Ready For Review` | A stage or final result awaits approval |
| `Ready To Apply` | Required input resolved; approved edits ready |
| `Validation Failed` | Tooling/validation needs repair |
| `Complete` | All in-scope statements `done`; no follow-up or price approval pending |
| `No Changes Made` | No eligible statements or ledger/status changes |
