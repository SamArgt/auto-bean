# Question-Handling Contract

Use this contract whenever an import stage encounters missing information, risky ambiguity, manual extraction needs, or a user decision that blocks safe progress.

## Core Rules

- Persist every deterministic result before asking or returning a question.
- Record unresolved items in the stage-owned artifact/status path before handing control back.
- Ask only bounded questions that name the affected statement, record, or ledger decision.
- Provide evidence-backed suggestions as often as possible, including a recommended default when the current facts support one.
- Keep observed facts, agent suggestions, risks of guessing, and user-editable answer fields visibly separate.
- Prefer one consolidated question set per stage/artifact over scattered one-off prompts.
- Resume the same stage or artifact after the answer, carrying the persisted context and the exact answer supplied.

## Minimum Question Fields

Each persisted or returned question should include:

- stable question id
- affected source path, parsed artifact, transaction, or ledger target
- observed facts
- why guessing is unsafe
- smallest useful set of choices or requested facts
- suggested answer or default choice when evidence supports one
- fields or decisions that may change after the answer
- artifact/status path where the question is recorded

## Human-Fillable Artifacts

When creating an artifact for question answering, make it easy for a human user to complete without editing surrounding context. Use stable question ids, concise observed facts, clear suggested defaults, checkboxes or short blanks, and explicit "leave blank if unknown" guidance. Put the suggested default first and make accepting it the easiest path, while keeping alternatives and free-form corrections available.

## Import-Invoked Broker Rule

When a worker stage is invoked by `$auto-bean-import`, the worker normally does not ask the user directly. It records safe progress, persists the question in its stage-owned artifact/status records, and returns the question summary to `$auto-bean-import`.

`$auto-bean-import` is the user-facing broker for import workflows. It asks the user in the main thread, batches compatible questions when useful, reads completed fillable artifacts, updates or resumes the owning stage with the answer, and keeps blocked statements out of downstream posting or final approval until the required answer is resolved.

Direct-use skills may ask the user themselves, but they must still persist safe progress first and resume the same task after the answer.

## Follow-Up Rule

If an answer is insufficient, ask one bounded follow-up that states the remaining blocker. Do not convert unresolved ambiguity into a guess, placeholder posting, accepted reconciliation decision, or final approval.
