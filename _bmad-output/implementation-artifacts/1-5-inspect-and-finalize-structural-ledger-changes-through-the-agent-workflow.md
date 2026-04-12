# Story 1.5: Inspect and finalize structural ledger changes through the agent workflow

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a trust-conscious user,
I want structural ledger changes summarized and shown through git-backed inspection before they are committed,
so that the agent cannot silently finalize changes that alter the meaning of my ledger.

## Acceptance Criteria

1. Given a direct structural change to the ledger or workspace, when the workflow finishes mutating and validating the result, then the system presents a concise summary plus `git diff` before commit/push finalization, and the user can explicitly approve or reject the commit/push step.
2. Given a structural change is approved for commit/push, when the workflow completes, then the resulting change is captured in inspectable history with diff visibility, and the system preserves an auditable trail for later revert-based rollback.

## Tasks / Subtasks

- [x] Reframe the authored structural-change workflow around direct mutation plus post-mutation inspection. (AC: 1, 2)
  - [x] Update `skill_sources/auto-bean-apply/SKILL.md` so routine structural edits are treated as direct workspace mutations that must be validated, summarized, and shown through `git diff` before commit/push approval.
  - [x] Keep optional proposal artifacts under `.auto-bean/proposals/` only for deeper inspection or unusually risky changes, not as the default safety model for every structural edit.
  - [x] Ensure the workflow language distinguishes clearly between "mutation happened in the working tree" and "change is accepted into history" so the agent never implies approval occurred before the user approves commit/push.
- [x] Align the shared mutation policy with the approved direct-adjustment architecture. (AC: 1, 2)
  - [x] Update `skill_sources/shared/mutation-pipeline.md` to match the current architecture sequence: build mutation intent, apply in the local workspace, run post-apply validation, produce diff and summary, request commit/push approval, then record audit outcome.
  - [x] Update `skill_sources/shared/mutation-authority-matrix.md` so mutation authority is described in terms of validation and commit/push gating rather than a proposal-first handoff.
  - [x] Preserve the trust boundary that canonical `ledger.beancount` and `beancount/**` changes are high-scrutiny operations even when direct mutation is now the normal path.
- [x] Define the minimum supporting runtime and audit behavior without introducing a new CLI-first workflow. (AC: 1, 2)
  - [x] Prefer authored skill behavior first and add Python helpers only where reusable support is needed for validation summaries, diff capture, approval-required responses, or audit artifact persistence.
  - [x] Keep supporting package work in the current flat package layout under `src/auto_bean/`, especially `src/auto_bean/init.py`, `src/auto_bean/cli.py`, and `src/auto_bean/smoke.py`, instead of reintroducing layered `application/`, `domain/`, or `infrastructure/` packages.
  - [x] Capture enough governed audit context under `.auto-bean/artifacts/` to explain what changed, whether validation passed, what approval decision was made, and which commit to revert if rollback is later needed.
- [x] Update generated-workspace guidance to match the new trust model. (AC: 1, 2)
  - [x] Revise `workspace_template/AGENTS.md` so it describes direct edits plus post-mutation validation and `git diff` inspection as the standard structural-change flow.
  - [x] Keep workspace guidance honest about what is supported now: explicit approval is required before commit/push, and rollback is git-backed rather than driven by a separate proposal-application phase.
  - [x] Avoid introducing or documenting nonexistent workspace docs surfaces; align guidance to the files that actually ship in `workspace_template/`.
- [x] Add deterministic coverage for the new inspection-and-finalization boundary. (AC: 1, 2)
  - [x] Extend focused tests such as `tests/test_setup_diagnostics.py`, `tests/test_smoke_checks.py`, and any relevant skill-contract coverage so they assert the direct-mutation, validation, diff, and approval sequence.
  - [x] Add or update smoke coverage for one representative approved structural-change path and one blocked or rejected finalization path.
  - [x] Verify that tests fail closed when validation fails, when approval is denied, or when commit/audit capture cannot complete.

## Dev Notes

- The April 12, 2026 approved sprint change proposal explicitly collapsed the old proposal-first import/apply model into direct ledger mutation with validation, git-backed inspection, and approval at the commit/push boundary. Story 1.5 is the Epic 1 story that establishes that trust model for structural ledger changes before later import and reconciliation stories build on it.
- Story 1.4 already creates the runtime workspace, initializes git, installs authored skills into `.agents/skills/`, and validates `ledger.beancount`. Story 1.5 should build on that existing workspace baseline instead of introducing a second workspace model or a parallel approval system.
- The product repo is not the live ledger workspace. Author workflow behavior in `skill_sources/` and supporting package files here; actual accepted ledger edits, diffs, commits, and rollback operations happen in generated user workspaces.
- The current repo layout is flat. Older artifact notes that mention `src/auto_bean/application/`, `domain/`, or `infrastructure/` are stale and should not drive implementation for this story.
- No separate UX artifact or `project-context.md` exists, so trust-sensitive behavior must stay explicit in the skill text, shared policy docs, workspace guidance, tests, and governed artifacts.

### Technical Requirements

- Keep the primary implementation surface in `skill_sources/auto-bean-apply/` and `skill_sources/shared/`.
- Treat Python as support for skill execution, validation, installation, smoke checks, and packaging, not as a replacement for the authored Codex-first workflow.
- Reuse the existing initialization/runtime expectations already enforced in `src/auto_bean/init.py` and `tests/test_setup_diagnostics.py`, including generated workspace scripts, git initialization, and workspace-local tool installation.
- Keep structured helper outputs in `snake_case` and local-file backed; there is still no public SDK or external API in scope.

### Architecture Compliance

- The architecture now defines the ledger-mutation pattern as: read inputs, normalize typed records, build mutation plan, apply mutation in the local workspace, run post-apply validation, produce diff and concise summary, ask whether to commit and push, then record audit outcome. Story 1.5 should implement the structural-change version of that exact pattern. [Source: `_bmad-output/planning-artifacts/architecture.md`]
- The architecture also states that no agent may mutate the ledger from parsed input without structured mutation intent, validation, presented diff and summary, and approval before commit/push finalization. This story should preserve that guardrail while removing the older proposal-only handoff assumption. [Source: `_bmad-output/planning-artifacts/architecture.md`]
- Keep the local-first trust boundary intact: git history, rollback, validation results, and audit context all stay in the workspace and on the user's machine. [Source: `_bmad-output/planning-artifacts/prd.md`]

### File Structure Requirements

- Likely files to create or modify when implementing this story:
  - `skill_sources/auto-bean-apply/SKILL.md`
  - `skill_sources/shared/mutation-pipeline.md`
  - `skill_sources/shared/mutation-authority-matrix.md`
  - `workspace_template/AGENTS.md`
  - `src/auto_bean/init.py` only if install-time scaffolding or helper scripts need to expose the updated approval model
  - `src/auto_bean/cli.py` only if a helper-facing result surface must reflect approval-required or audit information
  - `src/auto_bean/smoke.py`
  - `tests/test_setup_diagnostics.py`
  - `tests/test_smoke_checks.py`
  - `tests/test_import_skill_contract.py` only if shared review-handoff wording or installed-skill expectations change
- Do not add live runtime skills under product-repo `.agents/skills/`.
- Do not reintroduce proposal-only workflow scaffolding as the default path for structural changes.

### Testing Requirements

- Run `uv run ruff check` and `uv run ruff format` after code changes.
- Run `uv run mypy` when changing Python code.
- Run `uv run pytest` when changing Python code.
- Add deterministic tests for:
  - direct structural-change summaries that are shown after mutation and validation but before commit/push
  - `git diff` or equivalent diff-capture guidance being surfaced before approval
  - approval-denied and validation-failed flows that leave the change unfinalized
  - audit artifact capture that records approval outcome and commit metadata when a commit occurs
- Keep existing init and smoke-check coverage passing.

### Previous Story Intelligence

- Story 1.4 already established the generated workspace boundary, git initialization, workspace-local `.venv`, installed skills under `.agents/skills/`, and `ledger.beancount` as the stable validation entrypoint. Story 1.5 should reuse those seams directly.
- The older Story 1.5 artifact is now stale because it assumed a proposal-first trust model and pointed to outdated package paths. This regenerated story intentionally corrects both issues.
- Story 1.6 and Epic 2 stories rely on Story 1.5 as the structural trust boundary. Keeping the acceptance model centered on post-mutation inspection and commit/push approval will prevent later stories from rebuilding the removed proposal-first architecture.

### Git Intelligence

- Recent history shows the approved planning change landed in commit `a448f35` on April 12, 2026, updating `prd.md`, `architecture.md`, `epics.md`, and `sprint-status.yaml` together. Story 1.5 should follow that approved direction rather than the earlier done-state artifact.
- Prior story work keeps story artifacts and `sprint-status.yaml` synchronized. Maintain that pairing when implementing or advancing this regenerated story.

### Latest Technical Information

- Current Beancount documentation still describes `bean-check /path/to/file.beancount` as the standard validation command, which matches the workspace validation gate already surfaced by `auto-bean init` and `workspace_template/AGENTS.md`. Source: [Beancount docs](https://beancount.github.io/docs/index.html/getting_started_with_beancount)
- Current PRD and architecture language now agree that every meaningful ledger-changing workflow must produce validation output, a git-backed diff, and a concise change summary before the agent asks whether to commit and push the result. [Sources: `_bmad-output/planning-artifacts/prd.md`, `_bmad-output/planning-artifacts/architecture.md`]

### References

- [Epic breakdown](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/epics.md)
- [Sprint change proposal 2026-04-12](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-12.md)
- [Architecture](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/architecture.md)
- [PRD](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/prd.md)
- [Sprint status](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/sprint-status.yaml)
- [Previous story](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/1-4-create-a-new-base-beancount-ledger-workspace.md)
- [Apply skill source](/Users/sam/Projects/auto-bean/skill_sources/auto-bean-apply/SKILL.md)
- [Shared mutation pipeline](/Users/sam/Projects/auto-bean/skill_sources/shared/mutation-pipeline.md)
- [Shared mutation authority](/Users/sam/Projects/auto-bean/skill_sources/shared/mutation-authority-matrix.md)
- [Workspace agents guide](/Users/sam/Projects/auto-bean/workspace_template/AGENTS.md)
- [CLI entrypoint](/Users/sam/Projects/auto-bean/src/auto_bean/cli.py)
- [Init workflow](/Users/sam/Projects/auto-bean/src/auto_bean/init.py)
- [Smoke checks](/Users/sam/Projects/auto-bean/src/auto_bean/smoke.py)
- [Setup diagnostics tests](/Users/sam/Projects/auto-bean/tests/test_setup_diagnostics.py)
- [Smoke check tests](/Users/sam/Projects/auto-bean/tests/test_smoke_checks.py)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story 1.5 regenerated on 2026-04-12 after the approved sprint change proposal that removed the proposal-first structural workflow.
- Context synthesized from Epic 1, the April 12 sprint change proposal, the updated PRD and architecture, Story 1.4, current skill sources, current workspace template, current flat `src/auto_bean/` package layout, current tests, and recent git history.
- Corrected stale path guidance from the older Story 1.5 artifact so the next dev is pointed at real current files.
- Added Beancount validation guidance from current docs to keep the story aligned with the existing workspace validation gate.
- Updated the authored `auto-bean-apply` workflow and shared mutation policy to center direct working-tree mutation, post-mutation validation, `git diff` review, commit/push approval gating, and governed audit artifacts.
- Revised the generated workspace guidance and smoke helper coverage to reflect direct mutation plus git-backed rollback instead of a proposal-first structural flow.
- Verified the implementation with `uv run pytest tests/test_import_skill_contract.py tests/test_setup_diagnostics.py tests/test_smoke_checks.py`, `uv run ruff check`, `uv run ruff format`, `uv run mypy`, and `uv run pytest`.

### Completion Notes List

- Replaced the stale proposal-first Story 1.5 artifact with a ready-for-dev story aligned to the approved April 12 direct-mutation trust model.
- Synchronized the story filename and sprint tracker key with the updated Epic 1 title.
- Fixed downstream implementation-artifact links that referenced the obsolete Story 1.5 filename.
- Reframed the authored structural-change workflow around direct working-tree mutation, post-mutation validation, concise summaries, `git diff` inspection, and explicit commit/push approval.
- Aligned the shared mutation pipeline and authority matrix to the approved architecture while preserving high scrutiny for `ledger.beancount` and `beancount/**`.
- Updated generated-workspace guidance and deterministic coverage so the packaged workflow now documents audit-artifact capture, approval-denied behavior, and git-backed rollback expectations.

### File List

- skill_sources/auto-bean-apply/SKILL.md
- skill_sources/shared/mutation-pipeline.md
- skill_sources/shared/mutation-authority-matrix.md
- workspace_template/AGENTS.md
- src/auto_bean/smoke.py
- tests/test_import_skill_contract.py
- tests/test_setup_diagnostics.py
- tests/test_smoke_checks.py
- _bmad-output/implementation-artifacts/1-5-inspect-and-finalize-structural-ledger-changes-through-the-agent-workflow.md
- _bmad-output/implementation-artifacts/sprint-status.yaml

## Change Log

- 2026-04-12: Regenerated Story 1.5 after the approved sprint change proposal, aligning it with direct mutation plus post-mutation validation, diff inspection, and commit/push approval.
- 2026-04-12: Implemented Story 1.5 by updating the apply workflow, shared mutation policy, generated workspace guidance, smoke helper, and deterministic coverage for inspection-and-finalization gating.
