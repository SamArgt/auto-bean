# Story 1.5: Review and approve structural ledger changes through the agent workflow

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a trust-conscious user,
I want structural ledger changes to go through explicit review and approval,
so that the agent cannot silently alter the meaning of my ledger.

## Acceptance Criteria

1. Given a proposed structural change to the ledger or workspace, when a coding-agent skill prepares the change, then the skill summarizes the change in user-relevant context before it is finalized, and the user can explicitly approve or reject it.
2. Given the user wants deeper review context, when the skill is asked to do so, then it can create an inspectable proposal document or equivalent governed review artifact, and the user can validate the proposed change before it is committed.
3. Given a structural change is validated and approved, when the workflow completes, then the resulting change is captured in inspectable git history with diff visibility, and the system preserves an auditable trail for later review or rollback.

## Tasks / Subtasks

- [x] Introduce the first authored skill for structural-change review and approval, with Python code as supporting infrastructure rather than the primary user workflow. (AC: 1, 2, 3)
  - [x] Add authored skill content in the product repo for a structural review/apply workflow, following the architecture's markdown-first model.
  - [x] Ensure the installed runtime skill is the main surface the coding agent uses to summarize proposed structural changes, ask for validation, and only proceed after explicit user approval.
  - [x] Keep any CLI or Python entrypoints as helper surfaces for the skill, not as the primary approval UX.
  - [x] Reuse the Story 1.3/1.4 workflow result and event contract so the skill-backed execution still emits governed artifacts and stable status/error information.
- [x] Make the coding agent summarize structural changes in context before anything is committed. (AC: 1)
  - [x] Require the skill to explain what changed, why it changed, which files are affected, and why the change is safe or risky in the context of the user's ledger.
  - [x] Require the skill to distinguish between routine structural edits and materially meaningful changes that need extra scrutiny.
  - [x] Ensure the canonical ledger files under `beancount/` and `ledger.beancount` are not committed until the user has explicitly validated the proposed change.
  - [x] Keep this story scoped to structural ledger/workspace changes only; do not expand it to imported transactions, memory edits, or rollback automation yet.
- [x] Support optional proposal-document creation instead of making a proposal file mandatory for every run. (AC: 2)
  - [x] Allow the skill to create a governed proposal document or equivalent review artifact only when the user requests extra review context or when the change is risky enough to justify it.
  - [x] Store optional proposal documents and related review artifacts under governed workspace locations such as `.auto-bean/proposals/` and `.auto-bean/artifacts/`.
  - [x] Capture enough metadata for later review: requested change, affected files, validation status, approval decision, and any follow-up action needed from the user.
  - [x] Fail closed if the skill cannot produce the requested review context or if the proposal artifact becomes stale or invalid.
- [x] Require explicit validation and approval before the skill commits structural changes. (AC: 1, 2, 3)
  - [x] Make the skill ask the user to validate the proposed structural change after summary output and any optional proposal document are available.
  - [x] Run Beancount validation against `ledger.beancount` before the final commit path reports success.
  - [x] Commit only after the user has explicitly approved the validated change; do not imply that an unapproved change is already accepted.
  - [x] Ensure rejection or failed validation leaves the workspace uncommitted and preserves the review trail for later inspection.
- [x] Preserve inspectable git history and governed audit artifacts after approval. (AC: 3)
  - [x] Capture diff visibility through the workspace git repository and the agent summary presented to the user.
  - [x] Persist a governed audit artifact that records the reviewed change, validation outcome, user approval or rejection, and resulting commit information when a commit occurs.
  - [x] Ensure the audit trail is inspectable later without needing raw stack traces or conversational reconstruction.
- [x] Extend the workspace template and docs just enough to support the skill-first review model. (AC: 1, 2, 3)
  - [x] Add governed workspace directories or placeholders needed for optional proposal documents and audit artifacts, especially `.auto-bean/proposals/`.
  - [x] Update workspace-facing guidance such as `workspace_template/AGENTS.md` and `workspace_template/docs/README.md` so users understand that the coding agent should summarize structural changes, optionally prepare a proposal document, ask for validation, and only then commit.
  - [x] Update maintainer documentation to describe the authored-skill workflow, optional proposal document behavior, validation expectation, and commit-after-approval rule.
- [x] Add deterministic automated coverage for the skill-backed review lifecycle. (AC: 1, 2, 3)
  - [x] Add tests for skill-supporting services that create review summaries, optional proposal artifacts, validation results, approval-required responses, and final commit/audit behavior.
  - [x] Add tests for blocked flows such as missing validation, rejected approval, stale proposal artifact, failed Beancount validation, or failed git commit.
  - [x] Extend smoke coverage so CI exercises at least one representative skill-backed structural review flow and one blocked or rejected path.
  - [x] Verify that tests keep the user workflow centered on agent/skill interaction rather than forcing a CLI-only approval pattern.

## Dev Notes

- Story 1.4 created the first real user ledger workspace, initialized it as a git repository, and established `ledger.beancount` as the stable validation/Fava entrypoint. Story 1.5 should build on that runtime workspace rather than introducing a second workspace model.
- This story should realize the architecture's mutation pipeline through a coding-agent skill first: the agent summarizes changes, optionally writes a proposal document when needed, asks the user to validate, and only commits after explicit approval and successful validation.
- The architecture is explicit that only approved apply/recovery paths may modify `beancount/**`; proposal generation may write to `.auto-bean/proposals/**` and `.auto-bean/artifacts/**`, but not directly to canonical ledger sources.
- The architecture already says product development is primarily skill-driven. This story should therefore author the review behavior in skill markdown and add Python code only where reusable execution support is needed.
- Keep this story tightly scoped to structural ledger/workspace changes. It should establish the review-and-approval skeleton that later import and reconciliation stories can reuse, not attempt to solve transaction import review, rollback UX, or memory governance in full.
- No UX design artifact exists. Trust-sensitive behavior must therefore be carried by explicit agent summaries, structured result payloads, optional proposal documents, inspectable artifacts, and tests that prove the workflow fails closed when review conditions are not met.

### Technical Requirements

- Reuse the existing structured `WorkflowResult`, `DiagnosticCheck`, `WorkflowEvent`, and artifact-writing patterns instead of inventing a second workflow envelope underneath the skill.
- Add typed domain models for structural review summaries, optional proposal artifacts, approval decisions, validation outcomes, and audit summaries at service boundaries; do not pass ad hoc dictionaries across application/infrastructure layers.
- Treat approval as a hard trust boundary. The workflow must never imply that a mutation has been accepted or committed before user validation and post-change checks succeed.
- Use stable snake_case field names and error codes in helper outputs and governed artifacts.
- Wrap unexpected exceptions before they cross application boundaries and classify them with the existing error-category approach.

### Architecture Compliance

- Follow the architecture ledger-mutation pipeline exactly: build mutation plan, summarize changes for review, optionally produce a proposal artifact, validate, request approval, commit approved changes, and record audit outcome.
- Keep user-facing workflow behavior in authored skill content while keeping application services responsible for orchestration and infrastructure modules responsible for filesystem/git command side effects.
- Preserve the two-repository model: the product repo authors the workflow, while the user ledger repo holds proposals, artifacts, git history, and canonical Beancount files.
- Keep governed proposal and artifact files under `.auto-bean/`; do not mix review artifacts into `src/`, docs, or the canonical ledger source tree.
- Maintain the authority boundaries from architecture: this story may modify `.auto-bean/proposals/**` and `.auto-bean/artifacts/**`, but canonical `beancount/**` changes only become committed on the approved path.

### Library / Framework Requirements

- Continue using the existing Python packaged application structure with `uv`-managed workflows already established in the repo.
- Use git as mandatory workflow infrastructure for diff visibility and audit history; do not replace it with a custom non-git audit mechanism.
- Use Beancount validation against `ledger.beancount` as the correctness gate before the approved structural changes are committed.
- Keep result/artifact serialization aligned with the repo's current JSON artifact contract.
- Current official references confirm `git diff` supports direct file-or-directory comparisons, including `--no-index`, which is useful when comparing proposal material against canonical files before a change is committed. Source: [git-diff docs](https://git-scm.com/docs/git-diff)

### File Structure Requirements

- Likely new or extended product-repo surfaces for this story:
  - `skill_sources/` or the repo's chosen authored-skill source location for the structural review/apply skill
  - `src/auto_bean/application/` for a dedicated structural review/apply service
  - `src/auto_bean/domain/` for typed summary/proposal/approval/audit models
  - `src/auto_bean/infrastructure/` for governed proposal writing, diff generation, validation invocation, and git/audit helpers
  - `tests/` for unit, CLI, and smoke coverage
  - `workspace_template/.auto-bean/` for proposal-directory scaffolding
  - `workspace_template/docs/README.md` and `workspace_template/AGENTS.md` for workspace review guidance
- Do not collapse review/apply logic into the existing `setup.py` modules if a separate service module keeps boundaries clearer for later import/apply stories.
- Prefer adding real authored skill assets over building a CLI-only approval workflow. If the repo still lacks the final authored-skill source directory, create only the minimal structure needed for this story instead of inventing a large speculative catalog.

### Testing Requirements

- Keep all existing Story 1.1-1.4 tests, diagnostics, and smoke checks passing.
- Add deterministic coverage for:
  - agent-facing review summary generation without forcing immediate commit
  - optional proposal-document creation when requested
  - explicit rejection or missing validation leaving the canonical ledger uncommitted
  - successful approval and commit with post-change Beancount validation
  - blocked flows such as stale proposal artifact, invalid validation result, or failed git commit/audit step
  - representative skill-backed outputs and any helper JSON/human-readable artifacts they depend on
- Prefer temp-workspace tests and fake command runners over using a real user ledger repo.
- Keep smoke scenarios bounded so CI remains deterministic and fast.

### Previous Story Intelligence

- Story 1.3 established the stable workflow result envelope, governed artifact persistence, error categories, and deterministic smoke checks. Story 1.5 should extend those patterns directly underneath the skill flow.
- Story 1.4 established a generated workspace with `.git/`, `ledger.beancount`, helper scripts, `.agents/skills/`, and `.auto-bean/`; it also reinforced that structural trust comes from explicit inspection and fail-closed behavior.
- The current implementation already has strong seams in `src/auto_bean/application/setup.py`, `src/auto_bean/domain/setup.py`, and `src/auto_bean/infrastructure/setup.py`. Story 1.5 should follow those layering conventions while introducing review/apply support modules rather than overloading setup concerns.
- The current repo also lacks the actual structural review skill, proposal handling primitives, and validation-to-commit workflow. This story should establish those pieces in a reusable way so later import/reconciliation stories are not forced to invent them ad hoc.

### Git Intelligence

- Recent commits (`fb3131c`, `db681c2`) updated story artifacts, sprint status, README/docs, source modules, and tests together. Keep that synchronized pattern for Story 1.5 so authored skill behavior, helper code, docs, and tests ship together.
- Story 1.4 already initializes the runtime workspace as a git repo and creates an initial commit. Story 1.5 should leverage that baseline to provide inspectable history for approved structural changes instead of introducing a parallel audit trail.
- The repo still has no dedicated review/apply modules or authored structural-review skill, which makes this a good moment to establish a clean skill/service/infrastructure split for summaries, proposal persistence, validation, and commit handling.

### Latest Technical Information

- The official git documentation currently describes `git diff` as the standard mechanism to compare commits, working tree state, or filesystem paths, including directory-to-directory comparisons with `--no-index`; that makes it an appropriate primitive for the diff context the coding agent summarizes or stores in optional proposal artifacts for this story. Source: [git-diff docs](https://git-scm.com/docs/git-diff)
- Beancount documentation still uses `bean-check <file>` as the standard validation flow, and `ledger.beancount` remains the stable entrypoint already established by Story 1.4. Source: [Beancount Getting Started](https://beancount.github.io/docs/getting_started_with_beancount.html), [Running Beancount and Generating Reports](https://beancount.github.io/docs/running_beancount_and_generating_reports.html)
- The architecture and current repo state continue to favor skill-driven workflows with Python support code underneath them, so Story 1.5 should extend that model instead of introducing a CLI-led approval UX.

### References

- [Epic breakdown](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/epics.md)
- [Architecture](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/architecture.md)
- [PRD](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/prd.md)
- [Previous story](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/1-4-create-a-new-base-beancount-ledger-workspace.md)
- [Story 1.3](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/1-3-establish-the-ci-workflow-verification-and-diagnostics-baseline.md)
- [Sprint status](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/sprint-status.yaml)
- [README](/Users/sam/Projects/auto-bean/README.md)
- [Setup service](/Users/sam/Projects/auto-bean/src/auto_bean/application/setup.py)
- [Setup domain models](/Users/sam/Projects/auto-bean/src/auto_bean/domain/setup.py)
- [Setup infrastructure](/Users/sam/Projects/auto-bean/src/auto_bean/infrastructure/setup.py)
- [Workspace guide](/Users/sam/Projects/auto-bean/workspace_template/docs/README.md)
- [Workspace agents guide](/Users/sam/Projects/auto-bean/workspace_template/AGENTS.md)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story 1.5 created on 2026-04-03 from the first backlog story in `sprint-status.yaml`.
- Context synthesized from Epic 1, the PRD, the architecture document, Stories 1.3 and 1.4, the current CLI/setup implementation, current tests, workspace template files, and recent git history.
- Story scope was revised to make the coding agent skill the primary review surface: summarize changes in context, optionally create a proposal document, ask the user to validate, and only then commit.
- Story scope remained tight around structural proposal/review/commit behavior only so later import, reconciliation, rollback, and memory stories can reuse the approval skeleton without this story trying to solve all ledger mutation workflows at once.
- The current repo has no `project-context.md` and no UX artifact; trust-sensitive requirements were therefore carried directly in tasks, guardrails, and testing expectations.
- Reworked the implementation to follow the architecture more closely: authored skill behavior now lives under `skill_sources/`, and `auto-bean init` materializes those authored skills into the workspace runtime under `.agents/skills/`.
- Removed the earlier CLI-led review/apply experiment so the primary user workflow remains skill-first, with Python limited to workspace creation, skill installation, packaging, and validation helpers.
- Added a product-repo `AGENTS.md` to guide future agent work around repository boundaries, skill-source ownership, and the skill-first trust model.
- Verified the end-to-end behavior with `uv run ruff check src tests scripts`, `uv run mypy src tests scripts`, `uv run pytest`, and `uv run python scripts/run_smoke_checks.py`.

### Completion Notes List

- Added authored skill sources under `skill_sources/auto-bean-apply/` and `skill_sources/shared/` so the structural review/apply workflow and shared mutation policy are maintained in markdown-first source files.
- Updated `auto-bean init` to validate `skill_sources/` and install authored runtime skills into the created workspace under `.agents/skills/` instead of treating product-repo runtime copies as the source of truth.
- Added a product-repo `AGENTS.md`, updated workspace/maintainer guidance to point at the installed `auto-bean-apply` skill, and removed the earlier CLI-led review surface.
- Kept deterministic automated coverage focused on readiness, init, and smoke checks while validating that initialized workspaces receive the authored installed skills.

### File List

- .gitignore
- AGENTS.md
- README.md
- _bmad-output/implementation-artifacts/1-5-review-and-approve-structural-ledger-changes-through-the-agent-workflow.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- src/auto_bean/application/setup.py
- src/auto_bean/application/smoke.py
- src/auto_bean/cli/main.py
- src/auto_bean/infrastructure/setup.py
- skill_sources/auto-bean-apply/SKILL.md
- skill_sources/auto-bean-apply/workflow.md
- skill_sources/shared/mutation-authority-matrix.md
- skill_sources/shared/mutation-pipeline.md
- tests/test_package_foundation.py
- tests/test_setup_diagnostics.py
- tests/test_smoke_checks.py
- workspace_template/AGENTS.md
- workspace_template/docs/README.md
- workspace_template/.auto-bean/.gitkeep
- workspace_template/.auto-bean/artifacts/.gitkeep
- workspace_template/.auto-bean/proposals/.gitkeep

### Change Log

- 2026-04-03: Reworked Story 1.5 around authored `skill_sources/`, init-time installed runtime skills, repo/workspace agent guidance, and updated documentation/tests for the architecture-aligned skill-first workflow.
