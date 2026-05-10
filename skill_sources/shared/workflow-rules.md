# Auto Bean Workflow Rules

Purpose: shared execution rules for auto-bean skills. Skill-specific instructions still own their stage mechanics.

## Required References

If a required installed reference is missing, report the missing path and stop that stage rather than guessing. If an optional reference is missing, say what was unavailable and continue only when the remaining evidence is enough.

## Judgment

Be conservative with financial facts, explicit about uncertainty, and proactive only when the action is reversible, workflow-eligible, or already approved by workflow state. Durable memory requires clear eligibility provenance and post-write disclosure. Ledger history requires explicit user approval before finalization.

Treat evidence as strong only when at least two independent current facts agree, such as institution or account identity plus currency, external id plus amount/date, or statement account metadata plus current ledger account constraints. Memory alone never makes evidence strong or a match confident; it must match current evidence and remain advisory.

Workflow-specific JSON memory writes are owned by `$auto-bean-memory`. Main-thread orchestrators and direct main-thread write sessions may update `.auto-bean/memory/MEMORY.md` at session end with durable global user context; sub-agents must return suggested `MEMORY.md` edits instead of writing it.

## Fail-Closed Semantics

Fail closed means no guessing and no silent continuation past a material ambiguity, validation failure, ownership conflict, or unsafe path. Apply this invariant in order:

1. Persist any deterministic safe progress already produced in the stage-owned output or artifact, without inventing missing facts.
2. Update the stage status to the blocked state when that stage has a status model; if the skill is read-only or has no status model, do not invent one.
3. Record blocker details in the owning artifact or response surface: affected path or record id, evidence checked, why continuing would be unsafe, and what input or repair is required.
4. Return explicit blocker metadata to the caller or user, including required input, resume requirements, and any safe progress path.

If persisting safe progress itself would be unsafe, path-ambiguous, or outside ownership, skip that write and return the blocker with the concrete reason.

## Artifacts

Artifact language should be plain and reviewable. Internal returns may be compact and technical.

Artifacts should link to stage-owned detail rather than copying full warning, question, answer, reconciliation, parsed-statement, or ledger payloads across ownership boundaries.

Do not include raw statement dumps, full ledger excerpts, secret tokens, tax identifiers, full account numbers, or full card numbers in Markdown artifacts unless the user explicitly requires that exact value for review. Prefer redacted forms such as last four digits, stable row ids, source paths, and artifact links.

## Sub-agent handoff

When spawning a sub-agent, provide clear instructions on which skill to use, the relevant artifact paths, the expected return schema, any relevant memory context and its scope.
Tell the sub-agent to not ask for clarification or additional information from the user; all required context must be supplied in the handoff.
Tell the sub-agent to not edit `.auto-bean/memory/MEMORY.md` directly; it must return any suggested global-memory updates for the main thread to review and apply.
