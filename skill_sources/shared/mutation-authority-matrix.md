# Mutation Authority Matrix

- `auto-bean-apply`
  - Proposal creation: allowed under `.auto-bean/proposals/`
  - Audit artifacts: allowed under `.auto-bean/artifacts/`
  - Canonical ledger mutation: allowed only after explicit approval and validation
- Routine workspace review
  - May inspect diffs and summarize impact
  - Must not claim acceptance before the user approves
- Recovery and rollback workflows
  - Reserved for future dedicated recovery skills

Canonical `ledger.beancount` and `beancount/**` changes are trust-boundary operations.
