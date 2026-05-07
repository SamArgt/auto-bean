# Auto Bean Workflow Rules

Purpose: shared execution rules for auto-bean skills. Skill-specific instructions still own their stage mechanics.

## Required References

If a required installed reference is missing, report the missing path and stop that stage rather than guessing. If an optional reference is missing, say what was unavailable and continue only when the remaining evidence is enough.

## Judgment

Be conservative with financial facts, explicit about uncertainty, and proactive only when the action is reversible, workflow-eligible, or already approved by workflow state. Durable memory requires clear eligibility provenance and post-write disclosure. Ledger history requires explicit user approval before finalization.

Treat evidence as strong only when at least two independent current facts agree, such as institution or account identity plus currency, external id plus amount/date, or statement account metadata plus current ledger account constraints. Memory alone never makes evidence strong or a match confident; it must match current evidence and remain advisory.

## Artifacts

Artifact language should be plain and reviewable. Internal returns may be compact and technical.

Artifacts should link to stage-owned detail rather than copying full warning, question, answer, reconciliation, parsed-statement, or ledger payloads across ownership boundaries.

Do not include raw statement dumps, full ledger excerpts, secret tokens, tax identifiers, full account numbers, or full card numbers in Markdown artifacts unless the user explicitly requires that exact value for review. Prefer redacted forms such as last four digits, stable row ids, source paths, and artifact links.

For ownership boundaries, read `.agents/skills/shared/ownership-map.md`. For sub-agent returns to `$auto-bean-import`, read `.agents/skills/shared/sub-agent-return-examples.md`.
