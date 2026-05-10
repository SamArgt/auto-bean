---
name: auto-bean-import
description: Orchestrate statement imports from raw statement discovery through delegated processing, delegated categorization, user-input surfacing, ledger posting, validation review, and final summary. Use when the user asks to import statements, process new raw statements, run the import workflow, or continue work from `statements/raw/` and `statements/import-status.yml`.
---

Use this as the user-facing import entrypoint. Delegate mechanics to narrower skills instead of duplicating their procedures.

Always read before acting:

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

1. Read and follow `.agents/skills/auto-bean-import/references/import-1-discovery.md`
  - Create or refresh one status entry and import-owned artifact per raw statement.
  - Use the same artifact prefix for process, categorize, and import artifacts.
  - Respect the gates and close sub-agents before proceeding.
2. Read and follow `.agents/skills/auto-bean-import/references/import-2-account-inspection.md`
  - Resolve account review and opening-balance checks.
  - Respect the gates before proceeding.
3. Read and follow `.agents/skills/auto-bean-import/references/import-3-categorization-review.md`
  - Complete categorization handoff, cross-statement review, and user review before writing.
  - Respect the gates and close sub-agents before proceeding.
4. Read and follow `.agents/skills/auto-bean-import/references/import-4-write-final-review.md`
  - Complete write handoff, write-stage brokering, validation review, and final approval.
  - Respect the gates and close sub-agents before proceeding.
5. Read and follow `.agents/skills/auto-bean-import/references/import-5-memory-handoff.md`
  - Persist reusable learning through governed memory handoff only after stage context is available.
  - Respect the gates and close sub-agents before proceeding.
6. Completion checklist:
  - every in-scope statement has a current status entry and matching import-owned artifact
  - each completed stage recorded artifact paths, question ids, decisions, and gate result
  - no statement advanced past a blocked or unresolved review status
  - ledger mutations, validation results, and final approval state are reflected in import-owned artifacts
  - governed JSON memory candidates were routed through the memory handoff stage
  - durable and global `MEMORY.md` suggestions were reviewed and applied or skipped by the main thread
  - final response includes statement outcomes, artifact links, ledger/status changes, validation result, memory result, and remaining blockers or approvals

Use supporting references only at their trigger point:

- Read `.agents/skills/shared/memory-access-rules.md` before selecting governed memory hints for a stage handoff, using memory-derived suggestions in review, accepting or rejecting memory suggestions from sub-agents, persisting reusable learning, or handling memory conflicts.
- Read `.agents/skills/shared/import-status.example.yml` only when creating new status fields, auditing schema shape, or reconciling an unexpected status entry before updating it.

## Guardrails

- Follow the shared workflow rules for ownership boundaries, status management, question handling, sub-agent handoff, compact returns, and memory use.
- Follow the import artifact contract for import-owned artifact paths, contents, and update rules.
- Avoid reading all references files at once, read them in order and only when their trigger points are reached.
