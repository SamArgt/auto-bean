---
name: auto-bean-import
description: Import statements from discovery through processing, account inspection, categorization, ledger writing, validation, and final user review. Use for new statements or resumed imports tracked in statements/raw/ and statements/import-status.yml.
---

Read [plugin execution](../../references/plugin-execution.md), [workflow rules](../../references/workflow-rules.md), [status reading](../../references/import-status-reading.md), and workspace `.auto-bean/memory/MEMORY.md` before acting. Resolve packaged resources relative to this file and financial-data paths against the selected workspace.

Read [memory access rules](../../references/memory-access-rules.md) before selecting, using, reviewing, or persisting memory suggestions. Read the [status example](../../references/import-status.example.yml) when adding status fields, auditing schema, or reconciling unexpected entries.

## Orchestration

Use this as the user-facing entrypoint; narrower skills own processing, categorization, ledger queries, and transaction writing. Resume each statement from persisted status; skip stages without eligible work. Preserve unchanged review states and `done`; reprocess completed statements only for explicit rework. Continue unrelated safe work while other statements await input or review.

For processing, categorization, and writing, spawn one sub-agent per eligible statement, even for a single statement. Run serially only when sub-agents are unavailable, preserving the same contracts. Supply the selected workspace, actual packaged skill locations, relevant `MEMORY.md` context, source/parsed paths, status and retry metadata, shared artifact prefix, stage artifacts, selected memory with attribution, and expected compact return schema. Sub-agents persist questions and return ids, artifact paths, blockers, safe progress, validation, and memory suggestions; only the main thread asks the user or edits `MEMORY.md`.

Persist deterministic progress before questions or handoffs. Batch compatible questions, record answers in their owning artifacts, and resume the owning skill when regeneration or unfinished work is required. Never advance unresolved statements. Before writing a cohort, hold candidates whose transfer or duplicate decision depends on unresolved evidence from another in-scope statement.

## Import artifact

Own one Markdown artifact per raw statement at `.auto-bean/artifacts/import/<artifact_prefix>--import.md`; never combine statements into a batch artifact unless explicitly required. Derive the prefix from a safe raw-filename stem slug, adding the smallest parent-directory slug or fingerprint suffix needed for uniqueness. Share it with process and categorize artifacts. Create or refresh the artifact before leaving `raw_ready`.

Use stable ids for statements, questions, decisions, document references, posting handoffs, and memory candidates. Keep these sections when relevant:

| Section | Content |
| --- | --- |
| `# Import Decisions <artifact_prefix>` | `schema_version`, raw path, source fingerprint, `artifact_prefix`, `created_at`, `updated_at` |
| `## Artifact References` | Source, parsed, process, categorize, write/validation, memory references, matching status key |
| `## Questions` | Import-owned questions in full; stage-owned question ids, artifact paths, resume decisions |
| `## First-Seen Account Decisions` | Proposals, evidence, targets, approval/rejection/write state, validation |
| `## Document Reference Decisions` | Account, date, raw path, target, duplicate check, proposal/approval/reuse/rejection/block/write state, validation |
| `## Cross-Statement Review` | Paired artifacts and transaction refs, matched facts, decision state, posting impact |
| `## Posting Decisions` | Write inputs/results, validation, blockers, user approval context |
| `## Memory Attribution` | Records considered/used, current-evidence checks, influenced decisions, rejection reasons |
| `## Memory Candidates` | Provenance, originating artifact, review state, eligibility, deduplication |
| `## Ignored Or Rejected Inputs` | Unsafe paths, stale references, invalid suggestions, unresolved blockers, rejected candidates |

Persist import decisions before asking approval, handing off, invoking memory, or marking `done`; update `updated_at` on changes. Link stage-owned detail instead of copying it. Prefer compact tables, bullets, and short exact directive/validation blocks. Keep status, progress counts, queue position, retries, and transition history in the status index, not this artifact. Exclude raw dumps, full parsed JSON, ledgers, parser output, full memory files, and unrelated financial data.

Fail closed on unsafe artifact paths, conflicting prefixes, unreadable/unwritable artifacts, or conflicts with `statements/import-status.yml`.

## 1. Discovery and processing

- Inspect `git status --short` and `statements/import-status.yml`. Create/update `raw_ready` entries and import artifacts for new, changed, missing-status, or explicitly reprocessable statements, respecting persisted review/completion state. Fingerprint `.pdf`, `.csv`, `.xlsx`, and `.xls` sources.
- Inspect `.auto-bean/memory/import_sources/index.json`; select only narrowly matching `import_source_behavior` records using source identity, institution, owner/account hints, statement shape, filename pattern, or fingerprint. Record reuse attribution and current-evidence checks.
- Dispatch eligible `raw_ready` statements with current import artifacts to `$auto-bean:auto-bean-process`. Include expected parsed-output paths/naming, retry context, and selected source behavior. Require its process return schema; wait for all assigned agents to return `process_blocked`, `process_review`, or `account_review`, then close them before downstream handoff.
- Inspect process artifacts and broker warnings or questions for `process_review` and resolvable `process_blocked`. Record answers that change parsed evidence in the process artifact; record question ids, artifact/affected paths, and resume decisions in the import artifact. Resume processing only for parser regeneration/normalization. Move resolved review entries to `account_review`; retain unresolved process states.

## 2. Accounts and opening balances

- For `account_review` (or resumed `account_blocked`), use `$auto-bean:auto-bean-query` to inspect ledger accounts. Check selected source behavior and `.auto-bean/memory/account_mappings.json` against the shared strong-evidence threshold. Classify each account as `existing_account`, `first_seen_candidate`, or `blocked_inference`; record existing matches.
- Limit first-seen inference to institution-owned balance-sheet accounts and opening balances for banking, credit cards, loans, cash, and investments. Propose Beancount-safe names and minimal supporting directives only from strong current evidence. Present exact directives, target files, evidence, and why the account appears first-seen; obtain approval or correction before writing.
- For each parsed `statement_metadata.accounts[]` item, propose `YYYY-MM-DD document <ledger-account> "<raw-statement-path>"` using the statement period end, confidently matched ledger account, and parsed `source_file` under `statements/raw/`. Multi-account statements need one per matched account. Missing/uncertain account, date, or safe source path blocks the statement at `account_blocked`.
- Deduplicate documents by date, account, and raw-file path against the ledger. Follow existing directive placement or the narrowest file owning that account/date; ensure the encoded path resolves to the raw file from the target ledger file. Include document proposals in the import approval package; the same approval covers them unless the user rejects/changes them. Record decisions in `## Document Reference Decisions`.
- Keep `account_blocked` while identity, currency, target, duplicate risk, or approval is unresolved. Write only approved opening structure, document references, and minimal supporting directives; prefer `beancount/accounts.beancount` and `beancount/opening-balances.beancount` for account structure. Validate with `auto_bean bean-check ledger.beancount`, record decisions/results, then move resolved statements to `balance_review`.
- At `balance_review` (or resumed `balance_blocked`), query ledger balances at the statement opening boundary, respecting Beancount date semantics, and compare parsed opening balances. For mismatches or untrustworthy checks, show account, ledger/statement balances, and remediation choices; keep `balance_blocked` until resolved and any approved edits validate. Record the decision; only resolved statements reach `categorize_ready`.

## 3. Categorization and batch review

- Dispatch each `categorize_ready` parsed statement to `$auto-bean:auto-bean-categorize`, requiring its return schema. Wait for all categorize agents to return `categorize_review` or `categorize_blocked`, then close them. Keep clarification, repair, reconciliation, and manual-source blockers out of posting.
- Before presenting findings, inspect batch categorize artifacts and posting inputs, including blocked statements. Compare transfer/duplicate candidates using amounts, nearby dates, currencies, descriptions, references, fees, FX legs, and account pairs; query existing ledger activity through `$auto-bean:auto-bean-query` as needed. Do not silently drop, net, or mark duplicates without strong current evidence or approved input.
- For spanning candidates, add `Import Batch Cross-Statement Review` to each categorize artifact and record paired links, ids, summaries, and posting impact in import artifacts. Inspect other in-scope evidence/blockers before releasing a cohort; hold dependent candidates while unrelated resolved statements proceed.
- Broker categorize questions in the main thread, using provided fillable artifacts when useful. Record answers in categorize/import artifacts and update status. Resume categorization for unfinished work; move blocked statements to `categorize_review` only after resolved work is persisted. Only reviewed statements with resolved batch checks reach `write_ready`.

## 4. Writing and final approval

- Dispatch each `write_ready` statement to `$auto-bean:auto-bean-write` with parsed, process, categorize, and import artifact context. Record each return's changed files, validation, blocker/question ids, and artifact references. Broker questions and resume writing after answers; retain `write_blocked` during unresolved clarification, repair, or validation failure.
- Set `final_review` only after import transactions are written and validated. Query closing balances against parsed statement balances and reconcile status/artifact pointers; surface discrepancies before approval.
- Present per-statement review directly in the conversation: ledger changes, evidence/provenance, links/ids, decisions, risks, validation, and closing-balance results. Mark `done` only after explicit approval of that statement's final result; otherwise retain `final_review`. Close write agents after their completed statements reach `done`. Import owns finalization and commit/push readiness under shared rules.

## 5. Price epilogue

After import-owned ledger writes and current final-review decisions, invoke `$auto-bean:auto-bean-prices` once before memory handoff. Also resume pending price follow-ups from prior artifacts; skip fetching when there are neither new import-owned writes nor pending follow-ups.

Pass changed files, account/commodity hints, validation, and import artifact paths. Update active held and import-touched commodities using one explicit dated snapshot without `--update`; historical backfill needs a separate request. Broker source questions in the main thread. Require a terminal fetch state and reconciled job telemetry; running sessions or initially empty output are incomplete.

Keep price blockers separate from statement status; never move `done` backward for missing price sources. Report the price artifact, fetch mode, terminal state, exit code, duration, dry-run job count, directive and redundant/ignored counts, sanitized stderr, changed/skipped files, priced/skipped commodities, and post-price validation. Pass results (including blockers) and eligible `commodity_price_source` suggestions to memory handoff.

## 6. Memory and completion

After safe work and the price epilogue return, collect eligible suggestions from process, categorize, import, price, and supporting evidence. Invoke `$auto-bean:auto-bean-memory` once for the consolidated set, with provenance and current review state. Proactive writes are limited to eligible, governed, reversible advisory memory; unresolved blockers must not become durable learning. Memory never advances statement status or bypasses approval.

The main thread reviews durable/global `MEMORY.md` suggestions and applies or skips them. Before reporting, verify current status entries and import artifacts match, stage decisions/questions/results are persisted, and no unresolved gate was crossed. Summarize statement outcomes, artifact links, ledger/status changes, validation, price/memory outcomes, and remaining blockers or approvals.

## Final status block

End every user-facing import response with this block, with no text after it:

```markdown
---

## Import Status: <label>

**Summary:** <one concise sentence; include counts or statement paths when useful.>
**Next Step:** <one concrete user action, or "None." when Complete.>
```

Choose one label based on the most important remaining action:

| Label | Condition |
| --- | --- |
| `Needs Your Input` | Unresolved account, balance, category, write, validation, or source questions |
| `Ready For Review` | Process, account, balance, categorize, or final review needs approval |
| `Ready To Apply` | Required input resolved; approved changes ready to write |
| `Validation Failed` | Validation/tooling failed; next action is fixing it |
| `Complete` | Every in-scope statement is `done` and no import follow-up remains |
| `No Changes Made` | No eligible statements or no ledger/status changes |
