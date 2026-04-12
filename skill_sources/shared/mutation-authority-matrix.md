# Mutation Authority Matrix

- `auto-bean-import`
  - Direct working-tree mutation: allowed for first-seen account structure and minimal supporting directives derived from parsed statement evidence
  - Re-parsing source statements: allowed only to refresh `statements/parsed/` and `statements/import-status.yml`
  - Validation and diff inspection: required after mutation and before any finalization request
  - Proposal creation: optional under `.auto-bean/proposals/` for deeper review or risky diagnostics
  - Commit/push finalization: allowed only after explicit approval
  - Out of scope: transaction postings, reconciliation, duplicate handling, transfer handling, and durable memory writes
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
