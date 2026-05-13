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

- When a stage reference says to spawn a sub-agent, do that for independent statements when the runtime permits it.
- Include relevant `.auto-bean/memory/MEMORY.md` context in every sub-agent handoff.
- If sub-agents are unavailable, run the same stage serially and preserve all artifact, status, and return contracts.

## Workflow

Follow this ordered reference map; the stage mechanics live there. For each step, read its reference fully before acting, and wait to open the next reference until the current step is complete.

| stage | file to read | gate conditions | outputs |
| --- | --- | --- | --- |
| 1 discovery and processing | [import-1-discovery.md](references/import-1-discovery.md) | raw statements have current status entries and import artifacts; process sub-agents are closed or serial work is complete | status entries, process artifacts, parsed statements, compact process returns |
| 2 account inspection | [import-2-account-inspection.md](references/import-2-account-inspection.md) | account identity, currency, mutation target, duplicate risk, and approved account-opening needs are resolved or blocked | import artifact account decisions, status transitions, validation references |
| 3 categorization review | [import-3-categorization-review.md](references/import-3-categorization-review.md) | statements are at `categorize_review` or intentionally blocked; cross-statement transfer and duplicate review is resolved before writing, categorize subagents are closed | categorize artifact paths, compact question ids, posting handoff inputs |
| 4 write and final review | [import-4-write-final-review.md](references/import-4-write-final-review.md) | write sub-agents are closed; validation passes or blockers are recorded; final approval is explicit before `done` | ledger changes, validation results, final approval decisions, status updates |
| 5 price update epilogue | [import-5-price-update.md](references/import-5-price-update.md) | price-update sub-agent is closed or serial work is complete | active commodities with known sources are priced; unknown source mappings are blocked for review | price artifact, validation result, price memory suggestions |
| 6 memory handoff | [import-6-memory-handoff.md](references/import-6-memory-handoff.md) | memory example references selected by `$auto-bean-memory` | eligible reusable learning has provenance and review state; memory handoff is separate from statement advancement | governed memory result, `MEMORY.md` updates or skips, final summary |

Completion checklist:
  - every in-scope statement has a current status entry and matching import-owned artifact
  - each completed stage recorded artifact paths, question ids, decisions, and gate result
  - no statement advanced past a blocked or unresolved review status
  - ledger mutations, validation results, and final approval state are reflected in import-owned artifacts
  - governed JSON memory candidates were routed through the memory handoff stage
  - commodity price updates were attempted after import-owned ledger writes, with blockers surfaced rather than guessed
  - durable and global `MEMORY.md` suggestions were reviewed and applied or skipped by the main thread
  - final response includes statement outcomes, artifact links, ledger/status changes, validation result, memory result, price-update result, and remaining blockers or approvals

Use supporting references only at their trigger point:

- Read `.agents/skills/shared/memory-access-rules.md` before selecting governed memory hints for a stage handoff, using memory-derived suggestions in review, accepting or rejecting memory suggestions from sub-agents, persisting reusable learning, or handling memory conflicts.
- Read `.agents/skills/shared/import-status.example.yml` only when creating new status fields, auditing schema shape, or reconciling an unexpected status entry before updating it.

## Guardrails

- Follow the shared workflow rules for ownership boundaries, status management, question handling, sub-agent handoff, compact returns, and memory use.
- Follow the import artifact contract for import-owned artifact paths, contents, and update rules.
- Avoid reading all references files at once, read them in order and only when their trigger points are reached.
