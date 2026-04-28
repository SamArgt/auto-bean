# Sprint Change Proposal - Collapse Proposal-First Imports into Direct Ledger Mutation

## 1. Issue Summary

### Problem Statement

The current product design inserts a proposal-only structure-review layer between statement parsing and ledger mutation. In practice, that extra layer adds product complexity, splits responsibility across `auto-bean-import` and `auto-bean-apply`, and undermines the core value proposition of a simple agent-first workflow that saves time when importing statements.

This change was triggered by review of the current import architecture and skill boundaries:
- `auto-bean-import` is required to stop at parsed outputs and first-seen account proposals.
- `auto-bean-apply` is required to own the mutation boundary for structural ledger changes.
- the architecture treats `.auto-bean/proposals/` as a governed runtime state location for reviewable proposed changes.
- the user’s stated goal is to simplify the workflow so the agent edits the ledger directly once statements are parsed, using git inspection and rollback as the primary recovery mechanism.

### Issue Type

Failed approach requiring different solution, with elements of strategic simplification.

### Evidence

- The current `auto-bean-import` skill explicitly says it must “prepare reviewable first-seen account proposals without mutating the ledger.”
- The current `auto-bean-apply` skill explicitly says structural changes are reviewed and applied through a separate workflow.
- `architecture.md` defines a proposal-producing import stage and a separate apply boundary, including `.auto-bean/proposals/` as a first-class runtime storage area.
- `epics.md` splits import-derived structure creation, review of proposals, and later mutation approval into separate stages.
- Epic 2 stories `2-1` and `2-2` are already in `review`, which means the current implementation path is actively reinforcing the extra layer we now want to remove.

## 2. Checklist Summary

### Section 1: Understand the Trigger and Context

- `[x]` 1.1 Triggering stories identified: Epic 2 Stories 2.2 and 2.3, plus Epic 3 Story 3.4 and Epic 1 Story 1.5 by implication.
- `[x]` 1.2 Core problem defined: the proposal-first structure introduces friction that conflicts with the intended simple import experience.
- `[x]` 1.3 Supporting evidence gathered from current skills, PRD, architecture, epics, and sprint status.

### Section 2: Epic Impact Assessment

- `[x]` 2.1 Current epic remains viable only if its stories are rewritten around direct mutation rather than proposal handoff.
- `[x]` 2.2 Existing epics need modification rather than replacement.
- `[x]` 2.3 Future epics are affected, especially Epic 3 review/recovery flows and Epic 4 memory persistence triggers.
- `[x]` 2.4 No new epic is required, but one story likely becomes obsolete in its current form.
- `[x]` 2.5 Epic sequencing should shift slightly so direct import mutation is treated as the primary path and post-mutation inspection/recovery becomes the supporting safety layer.

### Section 3: Artifact Conflict and Impact Analysis

- `[x]` 3.1 PRD changes required.
- `[x]` 3.2 Architecture changes required.
- `[N/A]` 3.3 No separate UX artifact exists; trust-sensitive interaction requirements must stay in stories and skill guidance.
- `[x]` 3.4 Secondary artifacts requiring follow-up: `skill_sources/auto-bean-import/`, `skill_sources/auto-bean-apply/`, shared mutation policy docs, workspace template/runtime expectations, smoke checks, and story status tracking.

### Section 4: Path Forward Evaluation

- `[x]` 4.1 Option 1 Direct Adjustment: viable. Effort `Medium`, risk `Medium`.
- `[ ]` 4.2 Option 2 Potential Rollback: not preferred. Effort `High`, risk `Medium`.
- `[ ]` 4.3 Option 3 PRD MVP Review: not needed. Effort `Low`, risk `Low`, but does not solve the structural mismatch.
- `[x]` 4.4 Selected approach: `Option 1 - Direct Adjustment`, with a targeted de-scoping of the proposal layer.

### Section 5: Sprint Change Proposal Components

- `[x]` 5.1 Issue summary created.
- `[x]` 5.2 Epic and artifact impacts documented.
- `[x]` 5.3 Recommended path and rationale documented.
- `[x]` 5.4 MVP impact and high-level action plan defined.
- `[x]` 5.5 Agent handoff plan defined.

### Section 6: Final Review and Handoff

- `[x]` 6.1 Proposal is actionable and specific.
- `[x]` 6.2 Proposal is consistent with the requested direction.
- `[!]` 6.3 Explicit user approval still required before editing core planning artifacts and runtime skills.
- `[!]` 6.4 `sprint-status.yaml` should be updated only after approval.

## 3. Impact Analysis

### Epic Impact

#### Epic 1: Bootstrap a Safe Local Ledger Workspace

Epic 1 remains valid, but its trust language should stop implying that pre-apply proposal review is the default safety model. The quickstart should instead explain:
- direct agent edits are the normal path for routine imports
- validation is mandatory after each meaningful mutation
- git diff and rollback are the primary inspection and recovery tools
- the user approves commit and push after inspecting the direct mutation result

Story 1.5 is therefore semantically affected even if its current implementation is already marked `done`.

#### Epic 2: Import Statements and Introduce New Accounts Through Import

Epic 2 is the most heavily impacted epic.

The current version still assumes:
- first-seen accounts are proposed through import
- the user reviews structure and intake results before reconciliation
- ledger mutation is a later stage

The revised Epic 2 should instead own the direct import-to-ledger path:
- parse and normalize statements
- infer first-seen accounts from statement evidence
- write the required ledger updates directly when confidence is sufficient
- validate immediately
- summarize what changed and point the user to git diff/recovery when inspection is needed

Story 2.3 in its current form is no longer the right boundary and should be rewritten rather than preserved.

#### Epic 3: Reconcile and Inspect Ledger Changes Safely

Epic 3 remains necessary, but its focus shifts.

Instead of centering on review and approval of proposed mutations before application, Epic 3 should emphasize:
- transaction interpretation quality
- clarification loops for ambiguous cases before risky edits
- post-mutation validation
- git-backed inspection
- approval of commit/push after the direct mutation summary is presented
- rollback and troubleshooting

Story 3.4 is the clearest story that needs reframing because “review, validate, and approve proposed ledger mutations” reflects the architecture being removed.

#### Epic 4: Learn User Decisions and Improve Over Time

Epic 4 remains valid. The main adjustment is timing: memory should be persisted from accepted direct-import outcomes rather than from a separate proposal/apply phase.

#### Epic 5: Add Valuation Context for Multi-Asset Ledgers

No direct change is required.

### Artifact Conflicts

#### PRD Conflicts

The PRD currently conflicts with the requested change in several places:
- FR10 assumes proposal review for ledger-structure changes.
- FR18 implies review-before-acceptance in a way that currently reinforces proposal-first flow.
- FR35 and related safety language are written around pre-acceptance review artifacts.
- reliability wording requires an inspectable validation artifact and review artifact for every ledger-changing workflow, which over-specifies the current proposal model.

#### Architecture Conflicts

The architecture is materially aligned to the proposal-first design:
- it defines a dedicated review/apply boundary
- it elevates `.auto-bean/proposals/` to a governed runtime area
- it states that normalized parsed statement records flow into account proposal, review, and reconciliation services in later stages
- it defines mutation authority so only apply/recovery paths may modify `beancount/**`
- it explicitly says no agent may skip directly from parsed input to file mutation

Those are not implementation details; they are core architecture decisions that must be rewritten.

#### UX/Interaction Impact

No separate UX artifact exists. Interaction guidance must therefore be updated in stories and skills so the user experience stays trustworthy:
- routine direct edits should be narrated clearly
- the workflow should summarize direct edits and ask for approval before commit/push
- validation failure must never be represented as success
- git inspection and revert should be surfaced as the normal safety valves

#### Secondary Artifact Impact

Follow-up work will be needed in:
- `skill_sources/auto-bean-import/`
- `skill_sources/auto-bean-apply/`
- `skill_sources/shared/mutation-pipeline.md`
- `skill_sources/shared/mutation-authority-matrix.md`
- `src/auto_bean/init.py`
- `src/auto_bean/smoke.py`
- workspace template/runtime directory expectations involving `.auto-bean/proposals/`
- implementation stories currently in review

## 4. Recommended Approach

### Selected Path

Direct adjustment, classified as a major scope change.

### Rationale

This is the best path because it addresses the user’s actual concern instead of papering over it:
- it simplifies the user-facing workflow
- it removes duplicated conceptual layers between parsing, proposing, and applying
- it keeps safety through validation, post-mutation review, commit-time approval, and git-backed reversibility
- it better matches the product thesis that the agent is the primary operating interface, not a planner for a second workflow

### What Changes Conceptually

The trust model changes from:
- parse
- create proposal artifacts
- hand off to apply workflow
- ask for approval
- mutate ledger
- validate

To:
- parse
- infer direct ledger changes
- mutate ledger
- validate immediately
- summarize changes with `git diff` and workflow context
- ask for approval to commit and push the result
- revert the commit if a rollback is needed later

### Option Review

#### Option 1: Direct Adjustment

Viable: Yes
Effort: Medium
Risk: Medium

This keeps the existing product scope while simplifying the operating model.

#### Option 2: Potential Rollback

Viable: Limited
Effort: High
Risk: Medium

Rolling back already-reviewed implementation would only be justified if the existing in-flight changes are too proposal-centric to salvage. That should be decided during implementation, not at proposal time.

#### Option 3: MVP Review

Viable: No
Effort: Low
Risk: Low

The MVP does not need to shrink. The problem is not scope size; it is workflow shape.

## 5. Detailed Change Proposals

### PRD Changes

#### Functional Requirements

Requirement: `FR10`

OLD:
- `FR10: A user can review proposed ledger-structure changes before they are applied.`

NEW:
- `FR10: A user can inspect import-derived or agent-made ledger-structure changes through git-backed diffs and workflow summaries after direct mutation, then approve whether the agent should commit and push the result.`

Rationale: Keeps user control and trust, but moves approval to the commit boundary instead of a separate proposal phase.

Requirement: `FR18`

OLD:
- `FR18: A user can review imported results before accepting them into the ledger.`

NEW:
- `FR18: A user can inspect imported results, resulting ledger edits, validation outcomes, and a git-backed diff in a direct import workflow before approving commit and push.`

Rationale: Reorients the requirement around direct mutation plus post-mutation inspection instead of proposal review.

Requirement: `FR35`

OLD:
- `FR35: A user can review meaningful ledger changes before final acceptance.`

NEW:
- `FR35: A user can inspect meaningful ledger changes and their validation outcomes immediately after mutation, approve commit and push only after that inspection, and recover prior known-good state by reverting the commit when needed.`

Rationale: Moves trust from proposal acceptance to post-mutation inspectability plus commit-gated acceptance and recovery.

#### Reliability Requirement

OLD:
- `Every ledger-changing workflow shall produce an inspectable validation artifact and review artifact before the result is treated as accepted.`

NEW:
- `Every ledger-changing workflow shall produce an inspectable validation result, a git-backed diff, and enough local audit context to explain what changed before the agent asks whether to commit and push the result.`

Rationale: Preserves observability without forcing a dedicated proposal artifact for every mutation, while making the approval point explicit.

### Epic and Story Changes

#### Epic 2 Summary

OLD:
- `Users can import PDF, CSV, and Excel statements into a new or existing ledger, have first-seen accounts proposed through the import flow, review the resulting structure and transactions, and preserve source-specific context for repeat use.`

NEW:
- `Users can import PDF, CSV, and Excel statements into a new or existing ledger, let the agent write routine import-derived ledger updates directly when confidence is sufficient, inspect and recover changes through git-backed workflow controls, and preserve source-specific context for repeat use.`

Rationale: Makes direct mutation the default path instead of proposal handoff.

#### Story 2.2

Story: `2.2 Create or extend a ledger from first-time imported account statements`

OLD:
- `I want first-seen accounts to be proposed through statement import`
- `the system proposes the new account structure needed for that imported account as part of the import result`

NEW:
- `I want the agent to create or extend the ledger directly from first-time imported account statements when the evidence is sufficient`
- `the system writes the new account structure needed for that imported account directly into the ledger as part of the import workflow`
- `the workflow summarizes which files changed, what was inferred, and what should be inspected if the user wants review`
- `the workflow shows the resulting diff and asks whether the agent should commit and push the change`
- `if the evidence is insufficient, the structural inference is risky, or validation fails, the workflow pauses instead of guessing or finalizing`

Rationale: This is the core behavioral pivot requested by the user.

#### Story 2.3

Story: `2.3 Review normalized import results before finalizing direct ledger edits`

OLD:
- `Review normalized import results and first-seen account proposals before reconciliation`
- `review surface distinguishes parsed transaction records from structure changes such as first-seen account proposals`
- `workflow surfaces concerns clearly before reconciliation or ledger mutation proceeds`

NEW:
- `Review normalized import results, direct ledger edits, and validation outcomes in one import workflow`
- `the workflow distinguishes parsed statement facts from the ledger changes derived from them`
- `routine low-risk edits may be applied directly and then surfaced with validation results, git-backed inspection guidance, and an approval request for commit/push`
- `issues, low confidence, ambiguous inferences, or failed validation block commit/push until the user decides how to proceed`

Rationale: Preserves trust without preserving the old proposal boundary.

#### Story 3.1

Story: `3.1 Transform normalized import results into direct ledger postings with commit-gated acceptance`

OLD:
- `the system produces candidate ledger postings mapped to appropriate ledger accounts`
- `the result remains a proposal until later review and approval steps complete`

NEW:
- `the system transforms reviewed normalized import results into ledger postings and related edits`
- `routine high-confidence results may be written directly to the ledger`
- `the resulting change is summarized and shown through git-backed diff before commit/push`
- `ambiguous or risky results remain blocked pending clarification`

Rationale: Reframes reconciliation around direct execution with guarded escalation.

#### Story 3.4

Story: `3.4 Validate, inspect, approve, and recover ledger mutations safely`

OLD:
- `Review, validate, and approve proposed ledger mutations`
- `the user can inspect meaningful diffs between prior and proposed ledger state`
- `a proposed mutation set is approved for application`

NEW:
- `Validate, inspect, and recover ledger mutations safely`
- `the user can inspect meaningful diffs between prior and resulting ledger state`
- `post-change validation runs immediately after mutation`
- `the agent summarizes the change and asks whether to commit and push after inspection`
- `routine successful changes are treated as accepted only after validation succeeds and the user approves commit/push`
- `rollback is performed by reverting the recorded commit when needed`

Rationale: Keeps the safety promises while removing proposal-first semantics.

### Architecture Changes

#### Core Capability Framing

OLD:
- `ledger creation and structure management requirements establish that the system must create new ledgers, extend existing ledgers, propose structural changes, and require approval before risky structural edits.`

NEW:
- `ledger creation and structure management requirements establish that the system must create new ledgers and extend existing ledgers directly through agent workflows, then summarize the result and ask the user whether to commit and push the validated change.`

Rationale: The architecture should describe the simplified operating model directly and place approval at the commit boundary.

#### Data Flow

OLD:
- `normalized parsed statement records flow into account proposal, review, and reconciliation services in later workflow stages`
- `mutation plans flow into validation and review`
- `approved plans flow into ledger writer + git review pipeline`

NEW:
- `normalized parsed statement records flow into account inference and reconciliation services`
- `high-confidence results flow directly into ledger writer + validation`
- `validated results flow into git-backed inspection, approval for commit/push, and recovery support`
- `ambiguous or risky results flow into clarification checkpoints before finalization`

Rationale: Removes the mandatory proposal stage while preserving guarded escalation.

#### Authority Boundaries

OLD:
- `only approved apply/recovery paths may modify beancount/**`
- `import review and mutation-planning workflows may write .auto-bean/proposals/** and .auto-bean/artifacts/**`

NEW:
- `import and recovery workflows may modify beancount/** when they follow the standard mutation pipeline`
- `proposal artifacts become optional diagnostics rather than a required workflow boundary`
- `artifacts remain allowed under .auto-bean/artifacts/** for validation, troubleshooting, and audit context`
- `commit and push remain user-approved finalization steps after direct mutation and inspection`

Rationale: Aligns mutation authority with the direct import workflow.

#### Mutation Pipeline Rule

OLD:
- `No agent may skip directly from parsed input to file mutation.`

NEW:
- `No agent may mutate the ledger from parsed input without first deriving a structured mutation intent, validating the result, presenting the resulting diff and summary, and obtaining user approval before commit/push finalization.`

Rationale: The architecture should block unsafe shortcuts while matching the new commit-gated workflow.

#### Runtime Tree

OLD:
- `.auto-bean/proposals/ contains reviewable proposed changes`

NEW:
- `.auto-bean/proposals/ may exist temporarily for exceptional review or diagnostics, but it is no longer a required first-class runtime surface in the standard import workflow`

Rationale: Prevents the workspace shape from overfitting to a removed concept.

### Skill-Level Changes

#### `auto-bean-import`

OLD:
- parses statements and derives reviewable first-seen account proposals without mutating the ledger

NEW:
- parses statements, derives ledger edits directly when confidence is sufficient, validates the result, presents a change summary plus `git diff`, and asks whether to commit and push

Rationale: This becomes the primary ledger-mutation skill for import-driven workflows.

#### `auto-bean-apply`

OLD:
- separate review/apply workflow for structural ledger changes

NEW:
- reduced or repurposed into an exceptional inspection or recovery tool rather than a mandatory step for normal imports

Rationale: The product should not force a separate apply workflow when the import flow already owns safe mutation.

## 6. MVP Impact and Action Plan

### MVP Impact

The MVP remains achievable and likely improves:
- lower workflow complexity
- fewer handoff boundaries
- better alignment with “agent as primary interface”
- faster path from statement to usable ledger state

The trade-off is that safety must be expressed more carefully in validation, post-mutation inspection, commit-time approval, and recovery flows because pre-apply review will no longer do as much protective work.

### High-Level Action Plan

1. Approve this course correction.
2. Update `prd.md`, `epics.md`, and `architecture.md` to remove mandatory proposal-first semantics.
3. Update `sprint-status.yaml` to reflect renamed or re-scoped affected stories after approval.
4. Rewrite `skill_sources/auto-bean-import/` around direct mutation plus validation.
5. Reduce or repurpose `skill_sources/auto-bean-apply/`.
6. Update shared mutation policy docs to permit import-owned mutation authority with guarded escalation.
7. Update initialization, workspace template expectations, and smoke checks so `.auto-bean/proposals/` is no longer required for standard operation.
8. Re-assess in-flight Epic 2 implementation work so reviewed stories do not cement the deprecated model.

## 7. Implementation Handoff

### Scope Classification

Major

### Handoff Recipients

- Product Manager / Architect
  - approve the trust-model shift
  - finalize PRD and architecture wording
- Scrum Master / Product Owner
  - rewrite impacted stories and update sprint tracking
  - decide whether stories `2-1` and `2-2` need rework before merge
- Development
  - rework skills, helper code, smoke checks, and workspace expectations around the new direct-mutation flow

### Success Criteria

- The standard import flow no longer requires proposal artifacts or a separate apply skill to complete routine ledger updates.
- The standard import flow no longer requires proposal artifacts or a separate apply skill to complete routine ledger updates.
- Validation still runs after every meaningful mutation.
- The agent presents a summary plus `git diff` and asks for approval before commit/push.
- Rollback is handled by reverting the resulting commit when needed.
- Product docs, stories, and runtime expectations all describe the same operating model.

## 8. Approval Status

Proposal status: Draft, pending user approval.

Requested decision:
- `Continue` to apply the approved planning-artifact edits next
- `Edit` if you want to refine the proposal before I update `prd.md`, `epics.md`, `architecture.md`, and sprint tracking
