# Sprint Change Proposal - Clarify Import-to-Posting Transition

## 1. Issue Summary

Epic 2 currently implies that imported transactions are already in a form ready for acceptance, but the actual conversion from normalized import results into candidate ledger postings is only defined in Epic 3. This creates a sequencing gap between Stories 2.1, 2.2, 2.3, and 3.1.

The trigger was review of the Epic 2 flow:
- Story 2.1 creates a normalized intermediate representation
- Story 2.2 proposes account structure from imported account evidence
- Story 2.3 said the user reviews proposed imported transactions before acceptance
- Story 3.1 is the first place where transaction-to-posting conversion is explicitly defined

## 2. Impact Analysis

### Epic Impact

- Epic 2 remains valid, but its review story needed clarification so it does not imply ledger postings already exist.
- Epic 3 remains valid and now more clearly owns the missing transformation step from normalized import results to candidate ledger postings.
- No new epic is required.

### Artifact Impact

- `epics.md` required direct wording changes.
- `prd.md` is not in conflict; it already separates import, review, reconciliation, and validation at a higher level.
- `architecture.md` is not in conflict; it already states that normalized parsed statement records flow into later account proposal, review, and reconciliation stages.
- No UX artifact exists, so no UX update is required.

## 3. Recommended Approach

Recommended path: Direct adjustment.

Rationale:
- Lowest-risk fix.
- Preserves the existing five-epic structure.
- Aligns Epic 2 story wording with the architecture’s staged pipeline.
- Keeps FR20 in Epic 3, where transaction mapping belongs.

Effort estimate: Low
Risk level: Low
Timeline impact: Negligible

## 4. Detailed Change Proposals

### Stories

Story: 2.3 Review normalized import results and first-seen account proposals before reconciliation

OLD:
- Review import results before accepting transactions and structure changes
- user can review the proposed ledger effects before acceptance

NEW:
- Review normalized import results and first-seen account proposals before reconciliation
- user reviews normalized intake results before any candidate ledger postings are generated
- workflow explicitly states transaction-to-posting conversion happens in the later reconciliation stage

Rationale: Removes the implication that parsed statement rows are already ledger postings.

Story: 3.1 Transform normalized import results into candidate ledger postings

OLD:
- Map imported transactions into candidate ledger postings

NEW:
- Transform normalized import results into candidate ledger postings
- acceptance criteria now explicitly depend on Epic 2 import review having completed

Rationale: Makes the missing transformation step explicit and connects the epic boundary.

### Epic Summary

Epic 2 summary updated to describe review of intake and structure proposals before reconciliation, rather than review of already-formed transaction changes.

## 5. Implementation Handoff

Scope classification: Minor

Handoff:
- Product planning artifacts can proceed with the revised story wording.
- Future story implementation should treat `statements/parsed/` output as reviewable intake data, not ledger-ready postings.
- Reconciliation implementation should begin from reviewed normalized records and produce candidate mutation plans for later approval.
