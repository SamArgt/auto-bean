# Mutation Pipeline

Use this shared policy in any installed skill that can lead to ledger mutation.

1. Restate the requested change in plain language.
2. Inspect the affected files and summarize the proposed structural effect.
3. Distinguish routine edits from materially meaningful ledger changes.
4. Create a proposal artifact under `.auto-bean/proposals/` when the user asks for deeper review or when the change is risky enough to justify it.
5. Ask the user to validate the proposal before treating it as accepted.
6. Validate `ledger.beancount` before any approved apply path reports success.
7. Only proceed with an apply/commit path after explicit user approval.
8. Preserve governed artifacts under `.auto-bean/artifacts/` so later review does not depend on conversation history.

Never imply that a mutation is accepted before validation and explicit approval both succeed.
