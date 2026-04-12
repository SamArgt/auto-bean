# Mutation Authority Matrix

- `auto-bean-apply`
  - Direct working-tree mutation: allowed for scoped structural changes inside the local workspace
  - Post-mutation validation and summary: required before any finalization claim
  - Diff inspection: must present `git diff` or equivalent before commit/push approval
  - Proposal creation: optional under `.auto-bean/proposals/` for deeper or riskier review
  - Commit/push finalization: allowed only after explicit approval
  - Canonical ledger mutation: high-scrutiny operation; validation and commit/push approval are mandatory
- Routine workspace review
  - May inspect diffs and summarize impact
  - Must not claim acceptance into history before the user approves finalization
- Recovery and rollback workflows
  - May rely on git-backed history and recorded audit artifacts
  - Dedicated recovery skills can extend this later without weakening the approval gate

Canonical `ledger.beancount` and `beancount/**` changes are trust-boundary operations.
