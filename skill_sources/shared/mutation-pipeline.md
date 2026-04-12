# Mutation Pipeline

Use this shared policy in any installed skill that can lead to ledger mutation.

1. Restate the requested change in plain language.
2. Inspect the affected files and summarize the intended structural effect.
3. Distinguish routine edits from materially meaningful ledger changes, with extra scrutiny for `ledger.beancount` and `beancount/**`.
4. Apply the scoped mutation in the local working tree when it is within the workflow's authority.
5. Keep the mutation bounded to the workflow's scope; for import-driven account creation, that means account-opening structure and minimal supporting directives only.
6. Run post-apply validation before any commit or push step reports success.
7. Produce a concise summary plus `git diff` for the changed files before asking whether to finalize the change.
8. Treat that summary plus `git diff` as the review package before any finalization request.
9. In import-driven flows, distinguish parsed evidence from the derived ledger mutation so the user can review source facts separately from working-tree edits.
10. Treat any durable write under `.auto-bean/memory/import_sources/` as a governed operation; it must stay reviewable, bounded to source-specific import context, and only occur after a trustworthy finalized outcome.
11. If approval is denied, deferred, or blocked, leave the change unfinalized and record blocked or rejected outcomes under `.auto-bean/artifacts/` when durable troubleshooting context will help.
12. Create a proposal artifact under `.auto-bean/proposals/` only when the user asks for deeper review or when the change is risky enough to justify durable supplemental context.
13. If approval is granted, commit or push as approved.
14. Distinguish clearly between "the working tree changed" and "the change was accepted into history."

Never imply that a mutation is accepted into history before validation succeeds and explicit commit/push approval is granted.
