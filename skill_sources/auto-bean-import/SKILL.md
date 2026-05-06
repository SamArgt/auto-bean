---
name: auto-bean-import
description: Orchestrate statement imports from raw statement discovery through delegated processing, delegated categorization, user-input surfacing, ledger posting, validation review, and final summary. Use when the user asks to import statements, process new raw statements, run the import workflow, or continue work from `statements/raw/` and `statements/import-status.yml`.
---

Use this as the user-facing import entrypoint. Delegate mechanics to narrower skills instead of duplicating their procedures.

Always read before acting:

- `.agents/skills/shared/workflow-rules.md`
- `.agents/skills/shared/ownership-map.md`
- `.agents/skills/shared/import-status-reading.md`
- `.agents/skills/auto-bean-import/references/import-artifact-contract.md`

## Execution Model

- When a stage reference says to spawn a sub-agent, do that for independent statements when the runtime permits it.
- If sub-agents are unavailable, run the same stage serially and preserve all artifact, status, and return contracts.

## Workflow

Follow this ordered reference map. Read the matching file when a run reaches that stage; the stage mechanics live there.

1. `.agents/skills/auto-bean-import/references/import-1-discovery.md`
2. `.agents/skills/auto-bean-import/references/import-2-account-inspection.md`
3. `.agents/skills/auto-bean-import/references/import-3-categorization-review.md`
4. `.agents/skills/auto-bean-import/references/import-4-write-final-review.md`
5. `.agents/skills/auto-bean-import/references/import-5-memory-handoff.md`

Use supporting references only at their trigger point:

- `.agents/skills/shared/sub-agent-return-examples.md` when handing off or receiving a sub-agent stage.
- `.agents/skills/shared/question-handling-contract.md` before surfacing or resuming stage questions.
- `.agents/skills/shared/memory-access-rules.md` before using governed memory hints.
- `.agents/skills/shared/import-status.example.yml` only when creating new status fields or auditing schema shape.

## End With

Give a concise import-run summary with statement outcomes, artifact links, ledger or status changes, validation results, memory handoff result, and remaining approvals or blockers.

## Guardrails

- Follow the shared ownership map for process, categorize, write, query, and memory boundaries.
- Follow the import artifact contract for import-owned artifact paths, contents, and update rules.
