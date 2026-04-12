# Mutation Authority Matrix

- `auto-bean-import`
  - Direct working-tree mutation: allowed for first-seen account structure and minimal supporting directives derived from parsed statement evidence
  - Re-parsing source statements: allowed only to refresh `statements/parsed/` and `statements/import-status.yml`
  - Parsed statement outputs remain intake evidence until commit/push approval accepts any derived ledger mutation into history
  - In other words, parsed statement outputs remain intake evidence and are not accepted ledger history on their own
  - Validation and diff inspection: required after mutation and before any finalization request
  - Review surface: must separate parsed statement outputs from derived ledger edits and show validation outcome before approval is requested
  - Proposal creation: optional under `.auto-bean/proposals/` for deeper review or risky diagnostics
  - Commit/push finalization: allowed only after explicit approval
  - Blocked or rejected outcomes: may be recorded under `.auto-bean/artifacts/` as local audit context without changing accepted ledger history
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
