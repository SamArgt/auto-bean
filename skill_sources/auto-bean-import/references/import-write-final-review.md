# Import Write And Final Review

Use for write handoff, write-stage user brokering, validation review, and final import approval.

## Write Handoff

- For each `write_ready` statement, spawn a sub-agent and instruct it to use `$auto-bean-write` with import-owned and categorize artifact context.
- Broker any write-stage clarification through the shared question contract.
- Keep statements at `write_blocked` while write-stage clarification, repair, or validation fixes are unresolved.
- After user answers for `write_blocked`, resume `$auto-bean-write`.
- Set `final_review` only after import-derived transactions are written and validated.
- Gate: continue to final review only with statements at `final_review`.

## Final Review

- Verify relevant account balances against parsed statement closing balances with `$auto-bean-query`.
- Reconcile `statements/import-status.yml` against per-statement artifact references.
- Present final review by statement with links, ids, summaries, decisions, validation outcomes, provenance, and impact references.
- Mark entries `done` only after the user approves the final import result.
- Gate: close only statements at `done`; keep unapproved statements at `final_review`.
