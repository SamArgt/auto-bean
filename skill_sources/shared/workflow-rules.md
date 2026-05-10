# Auto Bean Workflow Rules

Purpose: shared execution, ownership, question-handling, and compact return rules for auto-bean skills. Skill-specific instructions still own their stage mechanics.

## Required References

If a required installed reference is missing, report the missing path and stop that stage rather than guessing. If an optional reference is missing, say what was unavailable and continue only when the remaining evidence is enough.

## Judgment

Be conservative with financial facts, explicit about uncertainty, and proactive only when the action is reversible, workflow-eligible, or already approved by workflow state. Ledger history requires explicit user approval before finalization.

Treat evidence as strong only when at least two independent current facts agree, such as institution or account identity plus currency, external id plus amount/date, or statement account metadata plus current ledger account constraints. Memory alone never makes evidence strong or a match confident; it must match current evidence and remain advisory.

## Question Handling

Use these rules whenever a workflow encounters missing information, risky ambiguity, manual extraction needs, or a user decision that blocks safe progress.

- Persist every deterministic result before asking or returning a question.
- Record unresolved items in the stage-owned individual artifact before handing control back.
- Ask only bounded questions that name the affected statement, record, transaction, or ledger decision.
- Provide evidence-backed suggestions as often as possible, including a recommended default when current facts support one.
- Keep observed facts, agent suggestions, risks of guessing, and user-editable answer fields visibly separate.
- Prefer one consolidated question set per stage or artifact over scattered one-off prompts.
- Treat missing account identity, transfer intent, duplicate suspicion, or source-specific meaning as clarification blockers rather than Beancount interpolation problems.
- Update the artifact after the answer, carrying the persisted artifact context and the exact answer supplied.

Each persisted question in the owning artifact should include:

- stable question id
- affected source path, parsed artifact, transaction, or ledger target
- observed facts
- why guessing is unsafe
- smallest useful set of choices or requested facts
- suggested answer or default choice when evidence supports one
- fields or decisions that may change after the answer
- artifact path where the question is recorded

When creating an artifact for question answering, make it easy for a human user to complete without editing surrounding context. Use stable question ids, concise observed facts, clear suggested defaults, checkboxes or short blanks, and explicit "leave blank if unknown" guidance. Put the suggested default first and make accepting it the easiest path, while keeping alternatives and free-form corrections available.

When a sub-agent stage is invoked by `$auto-bean-import`, the sub-agent NEVER asks the user directly. It records safe progress, persists the question in its stage-owned artifact, and returns only question ids, artifact path, and operational blocker flags to `$auto-bean-import`.

`$auto-bean-import` is the user-facing broker for import workflows. It asks the user in the main thread, batches compatible questions when useful, reads completed fillable artifacts, records answers in the relevant individual artifacts, updates or resumes the owning stage with the answer, and keeps blocked statements out of downstream posting or final approval until the required answer is resolved.

Direct-use skills may ask the user themselves, but they must still persist safe progress first, record the question and answer in the relevant individual artifact when an import artifact exists for the task, and resume the same task after the answer.

If an answer is insufficient, ask one bounded follow-up that states the remaining blocker. Do not convert unresolved ambiguity into a guess, placeholder posting, accepted reconciliation decision, or final approval.

## Fail-Closed Semantics

Fail closed means no guessing and no silent continuation past a material ambiguity, validation failure, ownership conflict, or unsafe path. Apply this invariant in order:

1. Persist deterministic safe progress already produced in the stage-owned output or artifact, without inventing missing facts.
2. Update the stage status to the blocked state when that stage has a status model; if the skill is read-only or has no status model, do not invent one.
3. Record blocker details in the owning artifact or response surface: affected path or record id, evidence checked, why continuing would be unsafe, and what input or repair is required.
4. Return explicit blocker metadata to the caller or user, including required input, resume requirements, and any safe progress path.

If persisting safe progress itself would be unsafe, path-ambiguous, or outside ownership, skip that write and return the blocker with the concrete reason.

## Artifact Boundaries

Artifact language should be plain and reviewable. Internal returns may be compact and technical.

Artifacts should link to stage-owned detail rather than copying full warning, question, answer, reconciliation, parsed-statement, or ledger payloads across ownership boundaries. For example, a categorize artifact should link to the relevant parsed statement and ledger evidence rather than copying large excerpts of them. An import-owned artifact should link to the relevant categorize artifact rather than copying its full content.

Do not include raw statement dumps, full ledger excerpts, secret tokens, tax identifiers, full account numbers, or full card numbers in Markdown artifacts unless the user explicitly requires that exact value for review. Prefer redacted forms such as last four digits, stable row ids, source paths, and artifact links.

## Ownership

| surface | owner |
| --- | --- |
| Raw statement discovery, import-owned artifacts, first-seen account structure, final import approval, commit and push readiness | `$auto-bean-import` |
| Raw-to-parsed processing, parsed statement evidence, process artifacts | `$auto-bean-process` |
| Statement categorization, reconciliation, deduplication, pending questions, posting inputs, categorize artifacts | `$auto-bean-categorize` |
| Transaction drafting and minimal transaction-supporting ledger directives | `$auto-bean-write` |
| Workflow-specific JSON memory and import-source memory files | `$auto-bean-memory` |
| Global profile memory (`MEMORY.md`) | Main-thread orchestrator or direct session; sub-agents return suggestions only |
| Ledger reads and analysis | `$auto-bean-query` |
| Import status index | Stage owner for its entry; operational pointers and compact flags only |

If a requested mutation is outside these owners, ask which workflow should own it instead of expanding a read-only or sub-agent skill.

## Sub-Agent Handoff

When spawning a sub-agent, provide clear instructions on which skill to use, what is its clear scope, the relevant artifact paths, expected compact return schema, and any relevant memory context.

Tell the sub-agent not to ask the user for clarification; all required context must be supplied in the handoff. Tell it not to edit `.auto-bean/memory/MEMORY.md` directly.

Use the same compact return style when running serially instead of through a sub-agent. Use empty lists or `null` for fields that do not apply, and follow the artifact boundaries above for detailed payloads.

Generic compact return example:

```yaml
assigned_path: statements/parsed/example.json
status_update:
  current_status: categorize_review
artifacts:
  process: .auto-bean/artifacts/process/example--process.md
  categorize: .auto-bean/artifacts/categorize/example--categorize.md
  import: .auto-bean/artifacts/import/example--import.md
blockers: []
pending_questions: []
safe_work_completed:
  - completed deterministic in-scope work
posting_inputs: []
memory_suggestions: []
memory_md_suggestions: []
mutation:
  changed_files: []
focused_diff_summary: null
validation:
  command: ./scripts/validate-ledger.sh
  result: passed
```
