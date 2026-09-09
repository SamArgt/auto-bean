---
name: auto-bean-import
description: Orchestrate statement imports from raw statement discovery through delegated processing, delegated categorization, user-input surfacing, ledger posting, validation review, and final summary. Use when the user asks to import statements, process new raw statements, run the import workflow, or continue work from `statements/raw/` and `statements/import-status.yml`.
---

Use this as the user-facing import entrypoint. Delegate mechanics to narrower skills instead of duplicating their procedures.

MUST read before acting:

- `.auto-bean/memory/MEMORY.md`
- `.agents/skills/shared/workflow-rules.md`
- `.agents/skills/shared/import-status-reading.md`
- `.agents/skills/auto-bean-import/references/import-artifact-contract.md`

## Execution Model

- When a stage reference says to spawn a sub-agent, spawn one sub-agent per eligible statement even when there is only one eligible statement.
- Include relevant `.auto-bean/memory/MEMORY.md` context in every sub-agent handoff.
- Run a stage serially only when sub-agents are unavailable, and preserve all artifact, status, and return contracts.

## Workflow

Use persisted per-statement status to enter or resume the appropriate stage in this reference map. Read that stage’s reference fully before acting; skip stages with no eligible work. Complete safe work for eligible statements while retaining blocked and review-pending statements at their current stage. Never reset later-stage or `done` statements merely to align a batch. Before writing, complete cross-statement review for the proposed posting cohort, holding any candidate whose transfer or duplicate risk depends on unresolved evidence from another statement.

| stage | file to read | gate conditions | outputs |
| --- | --- | --- | --- |
| 1 discovery and processing | [import-1-discovery.md](references/import-1-discovery.md) | raw statements have current status entries and import artifacts; process sub-agents are closed or serial work is complete | status entries, process artifacts, parsed statements, compact process returns |
| 2 account inspection | [import-2-account-inspection.md](references/import-2-account-inspection.md) | account identity, currency, mutation target, duplicate risk, and approved account-opening needs are resolved or blocked | import artifact account decisions, status transitions, validation references |
| 3 categorization review | [import-3-categorization-review.md](references/import-3-categorization-review.md) | statements are at `categorize_review` or intentionally blocked; cross-statement transfer and duplicate review is resolved before writing, categorize subagents are closed | categorize artifact paths, compact question ids, posting handoff inputs |
| 4 write and final review | [import-4-write-final-review.md](references/import-4-write-final-review.md) | write sub-agents are closed; validation passes or blockers are recorded; final approval is explicit before `done` | ledger changes, validation results, final approval decisions, status updates |
| 5 price update epilogue | [import-5-price-update.md](references/import-5-price-update.md) | import-owned ledger writes or a pending price follow-up require work; price update has a terminal result or recorded blocker | price artifact, validation result, price memory suggestions |
| 6 memory handoff | [import-6-memory-handoff.md](references/import-6-memory-handoff.md) | safe import work and any price epilogue have returned; memory stays separate from statement advancement | governed memory result, `MEMORY.md` updates or skips, final summary |

Completion checklist:
  - every in-scope statement has a current status entry and matching import-owned artifact
  - each completed stage recorded artifact paths, question ids, decisions, and gate result
  - no statement advanced past a blocked or unresolved review status
  - ledger mutations, validation results, and final approval state are reflected in import-owned artifacts
  - governed JSON memory candidates were routed through the memory handoff stage
  - commodity price updates were attempted after import-owned ledger writes, with blockers surfaced rather than guessed
  - durable and global `MEMORY.md` suggestions were reviewed and applied or skipped by the main thread
  - final response includes statement outcomes, artifact links, ledger/status changes, validation result, memory result, price-update result, and remaining blockers or approvals
  - final response ends with the required final status block below

## Final Status Block

User-facing import responses may include normal details first: list of clarifying questions, statement outcomes, artifact links, ledger/status changes, validation results, memory results, price-update results, blockers, and approval notes. After those details, every user-facing import response must end with this exact block shape. The block must be the last visible content in the response; do not add any text after it.

Use one batch-level status label, chosen from the most important remaining user action:

- `Needs Your Input`: any statement has unresolved account, balance, categorization, write, validation, or source-interpretation questions.
- `Ready For Review`: statements are in `process_review`, `account_review`, `balance_review`, `categorize_review`, or `final_review` and need user review or approval.
- `Ready To Apply`: all required input is resolved and the next action is applying/writing approved changes.
- `Validation Failed`: ledger validation or required tooling failed and the next action is fixing the reported failure.
- `Complete`: every in-scope statement is `done` and no import follow-up remains.
- `No Changes Made`: no eligible statements were found or the requested import produced no ledger/status changes.

The `Summary` line must be one concise sentence with counts or named statement paths when useful. The `Next Step` line must be one concrete user action, or `None.` when the status is `Complete`.

```markdown
---

## Import Status: <Needs Your Input | Ready For Review | Ready To Apply | Validation Failed | Complete | No Changes Made>

**Summary:** <one concise sentence describing what changed, what is ready, or what is blocked.>
**Next Step:** <one concrete action for the user, or "None.">
```

Examples:

```markdown
---

## Import Status: Needs Your Input

**Summary:** 12 transactions are drafted; 2 need category choices before writing can continue.
**Next Step:** Reply with accounts for the 2 listed transactions.
```

```markdown
---

## Import Status: Complete

**Summary:** 3 statements were imported, validated, priced, and marked `done`.
**Next Step:** None.
```

Use supporting references only at their trigger point:

- Read `.agents/skills/shared/memory-access-rules.md` before selecting governed memory hints for a stage handoff, using memory-derived suggestions in review, accepting or rejecting memory suggestions from sub-agents, persisting reusable learning, or handling memory conflicts.
- Read `.agents/skills/shared/import-status.example.yml` only when creating new status fields, auditing schema shape, or reconciling an unexpected status entry before updating it.

## Guardrails

- Follow the shared workflow rules for ownership boundaries, status management, question handling, sub-agent handoff, compact returns, and memory use.
- Follow the import artifact contract for import-owned artifact paths, contents, and update rules.
- Avoid reading all references files at once, read them in order and only when their trigger points are reached.
