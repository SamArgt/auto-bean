# Story 3.4: Validate, inspect, approve, and recover ledger mutations safely

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user reviewing direct ledger mutations,
I want validated post-change inspection, explicit finalization approval, and safe rollback guidance,
so that I can trust successful edits and recover cleanly when a result is wrong.

## Acceptance Criteria

1. Given the workflow writes ledger mutations into the working tree, when post-change review runs, then the system runs validation immediately after mutation, presents the resulting diff and concise change summary against the prior state, and asks whether to commit and push only after that inspection.
2. Given the validated result still contains warnings, blockers, or user concern, when the agent presents the review package, then it clearly distinguishes confirmed validation failures from inferred risks, preserves enough structured local audit context to explain what changed, and does not imply the result is accepted until commit/push approval is obtained.
3. Given a previously committed mutation later needs to be undone, when the user chooses recovery, then the workflow explains the relevant commit-backed rollback path, preserves the audit trail, and frames rollback as reverting the recorded commit rather than silently overwriting ledger state.

## Tasks / Subtasks

- [x] Strengthen the authored mutation workflow around post-apply validation and inspection. (AC: 1, 2)
  - [x] Update `skill_sources/auto-bean-apply/SKILL.md` and packaged prompt metadata so every ledger-changing path follows the standard sequence: draft mutation, run validation, present concise review context plus `git diff`, then request commit/push approval.
  - [x] Make the workflow language explicit that the inspected state is the resulting working-tree mutation, not a proposal artifact, and that acceptance happens only after successful validation plus user approval to finalize.
  - [x] Keep clarification and reconciliation findings inside the same review package so Story 3.4 consolidates the trust boundary rather than creating a second approval surface.
- [x] Define or tighten the review and audit artifact expectations for direct mutations. (AC: 1, 2)
  - [x] Ensure the authored guidance identifies the minimum structured diagnostics needed after mutation: validation outcome, changed files, affected statement status when applicable, reconciliation findings, and enough audit context to explain the change later.
  - [x] Keep artifact expectations local-first and file-backed under the governed artifacts area rather than relying on ephemeral chat history.
  - [x] Avoid reviving proposal-first artifacts as a required step; diagnostics and audit records should support direct mutation review, troubleshooting, and recovery.
- [x] Add safe finalization and rollback guidance without overscoping into a full new subsystem. (AC: 2, 3)
  - [x] Teach the workflow to describe commit/push approval as the hard finalization boundary and to leave working-tree mutations unfinalized when approval is denied, deferred, or blocked.
  - [x] Add or update authored guidance that explains rollback through git-backed history, emphasizing revert-based recovery of recorded commits instead of ad hoc file replacement.
  - [x] Keep rollback guidance scoped to trust-preserving recovery for committed mutations; full troubleshooting deep-dives and broader diagnostics UX remain for later story work.
- [x] Align packaged workspace guidance, initialization, and deterministic coverage with the mutation-safety boundary. (AC: 1, 2, 3)
  - [x] Update workspace guidance and README language only where needed so generated workspaces describe validation, inspection, commit/push approval, and rollback expectations consistently.
  - [x] Materialize any new authored mutation-safety references into the initialized workspace through `src/auto_bean/init.py`.
  - [x] Extend smoke and pytest coverage so required authored references and workspace-installed assets for the direct-mutation review path are verified deterministically.

## Dev Notes

- Story 3.4 is the trust-boundary consolidation story for Epic 3. Stories 3.1 through 3.3 already moved the product toward direct working-tree mutation with reconciliation findings and clarification checkpoints; this story makes the final validation, inspection, approval, audit, and recovery contract explicit.
- The 2026-04-12 course correction is authoritative here: proposal-first semantics were intentionally removed. The workflow should inspect the resulting post-mutation state, then ask whether to commit and push, with rollback performed later by reverting the recorded commit when needed.
- The product repo is not the runtime ledger workspace. Implementation should stay focused on authored skill behavior, packaged references, workspace guidance, init-time materialization, and deterministic verification so generated workspaces inherit the same mutation-safety model.
- No dedicated UX artifact or `project-context.md` was found. Interaction guidance therefore comes from Epic 3 wording, PRD trust requirements, the architecture mutation pipeline, the sprint change proposal, and the existing review boundary implemented across Stories 2.3, 3.1, 3.2, and 3.3.
- Current repo state matters: there is not yet a separate authored recovery skill in the product repo. Prefer extending the existing `auto-bean-apply` trust boundary and adding narrowly scoped references before introducing a new runtime surface.

### Technical Requirements

- Preserve the direct-mutation pipeline from the architecture: read reviewed inputs, derive typed mutation intent, apply the mutation in the local workspace, run post-apply validation, present concise review context and diff, then ask whether to commit and push.
- Keep `statements/import-status.yml` synchronized with the mutation state when import-derived postings are involved. `in_review` should remain the pre-finalization state for written-but-unfinalized transactions, and `done` should only follow successful validation plus explicit approval.
- Treat validation outcome, reconciliation findings, clarification effects, and changed files as one review package. The workflow should not imply acceptance merely because the working tree is updated.
- Preserve structured local audit context under `.auto-bean/artifacts/` or the current governed artifact path so suspicious results and later rollback decisions can be explained without reconstructing state from memory.
- Recovery guidance must prefer git-backed history. For committed mutations, rollback should be framed as reverting the recorded commit; do not silently overwrite ledger files or erase audit history.
- If Python support code is introduced for audit contracts, validation summaries, or packaged references, keep it flat and support-oriented in existing modules and follow the repo’s Pydantic v2 and `snake_case` expectations.
- Keep the workflow local-first and deterministic. Do not introduce hosted services, opaque caches, or database-backed audit state for this story.

### Architecture Compliance

- Architecture requires a single standard mutation pipeline for all ledger-changing operations, with validation and inspection after mutation and approval at the commit/push boundary.
- Validation, diff visibility, approval gating, auditability, and rollback are mandatory cross-cutting concerns, not optional workflow embellishments.
- The direct-mutation operating model remains in force: this story must not reintroduce mandatory proposal artifacts or pre-apply approval as the normal path.
- The runtime trust boundary remains local and file-backed. Audit context should live in governed artifacts, and rollback should leverage git-backed history.
- Clarification and reconciliation findings from Stories 3.2 and 3.3 should remain visible in the same final review package before finalization.

### Library / Framework Requirements

- Current Beancount guidance continues to treat balance assertions as checkpoints for verifying entered transactions; mutation review should preserve compatibility with that validation model when explaining failures or suspicious results.
- Current Beancount validation behavior also enforces currency constraints declared by `open` directives; post-mutation validation and review should treat those constraints as safety boundaries, not advisory hints.
- The workflow should continue to prefer explicit, inspectable postings even though Beancount can infer one missing amount in some cases, because Story 3.4 is about trustworthy review and recovery rather than opaque convenience.
- Ledger validation should remain a first-class post-apply step, typically through the existing workspace validation script or `bean-check`, before commit/push approval is requested.

### File Structure Requirements

- Likely files to create or modify when implementing this story:
  - `skill_sources/auto-bean-apply/SKILL.md`
  - `skill_sources/auto-bean-apply/agents/openai.yaml`
  - `skill_sources/auto-bean-apply/references/`
  - `workspace_template/AGENTS.md`
  - `README.md`
  - `src/auto_bean/init.py`
  - `src/auto_bean/smoke.py`
  - `tests/test_init.py`
  - `tests/test_smoke.py`
- Author skill behavior in `skill_sources/` first.
- Do not add live runtime skills under product-repo `.agents/skills/`.
- Materialize any new authored mutation-safety references into the user workspace during `auto-bean init`, not by editing installed runtime copies in the product repo.

### Testing Requirements

- Run `uv run ruff check` and `uv run ruff format` after code changes.
- Run `uv run mypy` when changing Python code.
- Run `uv run pytest` when changing Python code.
- Add deterministic coverage for:
  - required authored mutation-safety references being present in the repo
  - workspace materialization of any new review or rollback guidance references
  - workflow wording that keeps commit/push approval after validation and inspection
  - smoke coverage for the direct-mutation review and recovery assets

### Previous Story Intelligence

- Story 3.1 established the direct-posting path: import-derived candidate postings are written into the working tree, validated, shown with concise review context and `git diff`, and only then considered for commit/push approval.
- Story 3.2 added conservative reconciliation findings with explicit `warning` and `blocker` status. Story 3.4 should preserve those findings in the final review package rather than hiding them behind a new abstraction.
- Story 3.3 added the clarification checkpoint for ambiguous interpretations and required the workflow to show how user answers changed the drafted result before finalization. Story 3.4 should treat that explanation as part of the broader audit and inspection package.
- Story 2.3 already established that parsed facts, ledger edits, validation outcomes, and diff review belong together. Story 3.4 extends that same pattern into finalization and later rollback guidance.

### Git Intelligence

- Recent commits: `63d5c27 story 3.3`, `dc858a3 story 3.2`, `c197324 nit`, `65a3ee0 nit`, `d5cabf0 wip`.
- Recent Epic 3 work has consistently landed as authored skill updates plus workspace guidance, packaging, and deterministic coverage. Story 3.4 should follow that same shape instead of landing as a documentation-only idea or a runtime-only code change.
- The repo still lacks a dedicated authored recovery skill, which is a useful guardrail for scope: strengthen the direct-mutation review contract first, and introduce a new runtime surface only if the resulting interaction boundary genuinely requires it.

### Latest Technical Information

- Context7 Beancount docs confirm that `open` directives can enforce account currency constraints during validation, which means post-mutation review should treat those failures as concrete safety signals rather than stylistic warnings.
- The same docs describe balance assertions as checkpoints that help verify transaction entry correctness, which aligns with using validation output as part of a trust-preserving review package.
- Current Beancount guidance continues to favor explicit accounting outcomes that can be inspected and explained; this supports keeping the workflow’s mutation review and rollback path concrete rather than hidden behind automation.

### References

- [Epic breakdown](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/epics.md)
- [PRD](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/prd.md)
- [Architecture](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/architecture.md)
- [Sprint change proposal 2026-04-12](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-12.md)
- [Sprint status](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/sprint-status.yaml)
- [Story 2.3](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/2-3-review-normalized-import-results-before-finalizing-direct-ledger-edits.md)
- [Story 2.4](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/2-4-persist-source-specific-import-context-for-repeated-imports.md)
- [Story 3.1](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/3-1-transform-normalized-import-results-into-direct-ledger-postings-with-commit-gated-acceptance.md)
- [Story 3.2](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/3-2-detect-transfers-duplicates-and-unbalanced-outcomes-during-reconciliation.md)
- [Story 3.3](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/3-3-run-clarification-workflows-for-ambiguous-or-unfamiliar-transaction-patterns.md)
- [Apply skill source](/Users/sam/Projects/auto-bean/skill_sources/auto-bean-apply/SKILL.md)
- [Workspace agents guide](/Users/sam/Projects/auto-bean/workspace_template/AGENTS.md)
- [README](/Users/sam/Projects/auto-bean/README.md)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Tighten the authored `auto-bean-apply` workflow so the final trust boundary is explicit: post-apply validation, concise inspection, commit/push approval, and recoverable git-backed history.
- Keep the review flow direct: present the changed working-tree result plus validation and diff, then ask for commit/push approval without introducing a separate mutation artifact requirement.
- Align workspace guidance and deterministic coverage so generated workspaces inherit the same mutation-safety expectations.

### Debug Log References

- Story 3.4 created on 2026-04-22 from the current `epics.md`, `prd.md`, `architecture.md`, sprint change proposal dated 2026-04-12, `sprint-status.yaml`, Stories 3.2 and 3.3, current authored apply workflow docs, workspace guidance, product initialization/smoke surfaces, and recent git history.
- No dedicated UX artifact or `project-context.md` was available, so interaction requirements were derived from Epic 3 wording, PRD trust requirements, architecture mutation-pipeline rules, and the course-corrected direct-mutation operating model.
- Context7 Beancount docs were consulted to keep the story’s validation, currency-constraint, and balance-check notes aligned with current Beancount guidance.
- Implemented the mutation-safety contract by extending `auto-bean-apply`, keeping the post-mutation review direct, updating workspace and README guidance, and tightening the affected workflow assertions.
- Validation passed with `uv run pytest tests/test_apply_skill_assets.py tests/test_init.py tests/test_smoke.py`, `uv run ruff check`, `uv run ruff format`, `uv run mypy`, `uv run pytest`, and `uv run python scripts/run_smoke_checks.py`.

### Completion Notes List

- Selected the first backlog story in sprint order: `3-4-validate-inspect-approve-and-recover-ledger-mutations-safely`.
- Created a ready-for-dev story that consolidates Epic 3’s direct-mutation trust boundary around post-apply validation, inspection, commit/push approval, and revert-based rollback guidance.
- Kept the story grounded in the repo’s current product shape by centering authored skill behavior, packaged references, workspace guidance, init-time materialization, and deterministic coverage.
- Avoided assuming a pre-existing recovery skill; the story explicitly treats a separate runtime surface as optional and scope-dependent.
- Tightened the authored `auto-bean-apply` workflow so the inspected state is the resulting working-tree mutation, not a proposal artifact, and so commit/push approval remains the only finalization boundary.
- Kept the post-mutation review lightweight: present the changed files, validation outcome, findings, and `git diff` directly instead of requiring a separate mutation artifact.
- Updated workspace guidance and README language so generated workspaces consistently describe direct validation, inspection, and git-backed rollback expectations.
- Trimmed the affected assertions and coverage back to the direct review flow without requiring an extra packaged mutation-review reference.

### File List

- _bmad-output/implementation-artifacts/3-4-validate-inspect-approve-and-recover-ledger-mutations-safely.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- README.md
- skill_sources/auto-bean-apply/SKILL.md
- skill_sources/auto-bean-apply/agents/openai.yaml
- tests/test_apply_skill_assets.py
- workspace_template/AGENTS.md

### Change Log

- 2026-04-22: Implemented Story 3.4 by tightening the direct-mutation review boundary, keeping review output direct in-chat, updating workspace guidance, and validating the resulting coverage.
