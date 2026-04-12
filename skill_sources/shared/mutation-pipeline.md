# Mutation Pipeline

Use this shared policy in any installed skill that can lead to ledger mutation.

1. Restate the requested change in plain language.
2. Inspect the affected files and summarize the intended structural effect.
3. Distinguish routine edits from materially meaningful ledger changes, with extra scrutiny for `ledger.beancount` and `beancount/**`.
4. Apply the scoped mutation in the local working tree when it is within the workflow's authority.
5. Run post-apply validation before any commit or push step reports success.
6. Produce a concise summary plus `git diff` for the changed files before asking whether to finalize the change.
7. Create a proposal artifact under `.auto-bean/proposals/` only when the user asks for deeper review or when the change is risky enough to justify durable supplemental context.
8. Ask for explicit approval before commit or push finalization.
9. If validation fails or approval is denied, stop before finalization and record the blocked or rejected outcome under `.auto-bean/artifacts/`.
10. If approval is granted, commit or push as approved.

Never imply that a mutation is accepted into history before validation succeeds and explicit commit/push approval is granted.
