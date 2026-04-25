# Clarification Guidance

Use this reference when categorization, reconciliation, or deduplication remains blocked on ambiguity, unfamiliar source meaning, or low-confidence interpretation.
Keep clarification bounded, concrete, and easy for the user to answer.

## Purpose

- Clarification is a checkpoint before the import workflow posts categorized transactions.
- It is not a second approval system and not a generic chat loop.
- Use it only when the workflow cannot safely proceed from current evidence, ledger context, category/account suggestions, and reconciliation findings alone.

## How to ask

- Return only the minimum bounded questions needed to unblock the risky interpretation.
- Let `$auto-bean-import` ask the user unless it explicitly delegated that interaction to this skill.
- Before returning questions, persist every safe partial result and record unresolved questions in the parsed artifact, status entry, or `.auto-bean/artifacts/categorize/` so a restarted process can resume from the checkpoint.
- Continue unrelated safe work for the affected artifact before returning questions; do not stop at the first ambiguous row when later rows can still be categorized, reconciled, or deduplicated safely.
- Wait for the user answer before continuing unresolved decisions for the affected artifact.
- Lead with observed facts, then separate them from inferences.
- Name the plausible interpretations that remain on the table.
- Explain the risk of guessing wrong in concrete ledger terms.
- Prefer specific decisions such as account choice, transfer intent, duplicate handling, or institution-specific meaning.
- Avoid open-ended interrogation when a targeted choice will unblock the workflow.

## How to resume

- After `$auto-bean-import` supplies the user answer, update the persisted categorization or finding artifacts to reflect that answer.
- Resume the same artifact from persisted artifacts and status; do not throw away earlier safe work or treat clarification as a terminal blocked state.
- Show how the answer changed the category suggestion, reconciliation finding, deduplication decision, or posting input.
- Re-run reconciliation and deduplication checks if the clarification changed the interpretation.
- If the answer is still ambiguous, contradictory, or insufficient, return one bounded follow-up question or report the remaining blocker to `$auto-bean-import`.

## Reuse boundary

- Clarified outcomes may inform later governed memory work, but this story does not authorize broad autonomous preference learning.
- Keep every reusable outcome attributable to current evidence and the specific user answer that changed the result.
- When a clarified answer reveals a narrow source-specific rule that would help future imports, suggest a bounded `$auto-bean-memory` persistence request.
- Do not persist memory automatically. Keep the suggestion reviewable and bounded to the current source behavior.
