# Import handoff

Read before presenting questions or approval review, including on resume. Import owns this procedure; workers return findings to Import.

## Consolidated handoff

Use one user handoff per preparation pass, including resume:

1. Collect questions in existing inline review fields and price-run records. Workers return completed work or persisted blockers without waiting for user answers. Finish independent work and runnable follow-ups, including cross-group transfer and duplicate checks. Before handoff, every dispatched worker must have returned or stopped at a persisted blocker, with no writes still running. A blocked worker counts as settled; an active worker does not.
2. Prepare available price follow-ups after statement preparation and before handoff, under [Prices and Memory](../SKILL.md#prices-and-memory). Reread saved answers and have the owning stage apply them. Remove questions resolved by answers, ledger evidence or other statements. Complete any newly unblocked work before presenting the remaining questions.
3. Identify payment questions by source/account/record IDs and price questions by run/commodity IDs. Combine related rows only when one answer resolves them, such as a charge and reversal. Keep unresolved linked transfers held.
4. Run stable review validation and repair actionable errors under [Review, write and validate](../SKILL.md#review-write-and-validate). Open the review panel once for this stable handoff. Present the consolidated question set or approval review once in chat, with the final status and next action. Do not duplicate the questions through both a question tool and the final response. Transaction and price approvals remain separate in scope.

Keep progress updates informational. Do not ask questions or open review during preparation unless the user explicitly requests an early view; label that view incomplete. On resume, consume saved answers before reopening review. Ask only remaining or newly discovered questions after dependent work settles. If the panel is unavailable, report it and give the same consolidated review in chat; do not repeatedly retry opening it during that pass. A later approval review after clarification is a new handoff, not approval implied by the answers.

## Final status block

End consolidated handoffs, including clarification requests, with this block. Omit it from progress updates.

```markdown
---

## Import Status: <label>

**Summary:** <outcome, counts/paths.>
**Next Step:** <one user action, or "None." when Complete.>
```

Use `Needs Your Input` for unresolved choices; `Ready For Review` for pending approval; `Ready To Write` for approved unwritten transactions; `Validation Failed` for required repair; `Complete` only when all in-scope groups are done with no price/follow-up approval pending; or `No Changes Made` when no eligible work or state change occurred.
