# Clarification Guidance

Use this reference when reconciliation remains blocked on ambiguity, unfamiliar source meaning, or low-confidence interpretation.
Keep clarification bounded, concrete, and easy for the user to answer.

## Purpose

- Clarification is a checkpoint inside the existing validation-plus-diff review workflow.
- It is not a second approval system and not a generic chat loop.
- Use it only when the workflow cannot safely proceed from current evidence, ledger context, and candidate postings alone.

## How to ask

- Ask only the minimum bounded questions needed to unblock the risky interpretation.
- Use the appropriate user-input tool or conversation channel for the active workflow; do not force clarification through a specific skill unless that skill owns the work being clarified.
- Wait for the user answer before continuing the affected artifact.
- Lead with observed facts, then separate them from inferences.
- Name the plausible interpretations that remain on the table.
- Explain the risk of guessing wrong in concrete ledger terms.
- Prefer specific decisions such as account choice, transfer intent, duplicate handling, or institution-specific meaning.
- Avoid open-ended interrogation when a targeted choice will unblock the workflow.

## How to resume

- After the user answers, update the drafted workspace changes to reflect that answer.
- Resume the same artifact or transaction-writing task; do not treat clarification as a terminal blocked state.
- Show how the answer changed the pending result before any final approval request.
- Re-run reconciliation checks and validation if the clarification changed the drafted postings or supporting directives.
- If the answer is still ambiguous, contradictory, or insufficient, ask one more bounded follow-up, wait again, and then resume or report the remaining blocker to the calling workflow.

## Reuse boundary

- Clarified outcomes may inform later governed memory work, but this story does not authorize broad autonomous preference learning.
- Keep every reusable outcome attributable to current evidence and the specific user answer that changed the result.
- When a clarified answer reveals a narrow source-specific rule that would help future imports, suggest a bounded `$auto-bean-memory` persistence request.
- Do not persist memory automatically. Keep the suggestion reviewable and bounded to the current source behavior.
