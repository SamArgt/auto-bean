# Story 3.3: Run clarification workflows for ambiguous or unfamiliar transaction patterns

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user facing ambiguous import results,
I want the agent to ask targeted clarification questions and explain uncertainty,
so that I can correct the result without losing trust in the workflow.

## Acceptance Criteria

1. Given imported transactions contain ambiguity, unfamiliar patterns, or low-confidence interpretations, when the reconciliation workflow cannot proceed safely, then the agent requests clarification before applying a risky interpretation, and it explains why it is uncertain in terms the user can act on.
2. Given the user provides clarification, when the workflow resumes, then the system applies the clarification to the current reconciliation result, and the corrected interpretation can later be reused through the governed memory path.

## Tasks / Subtasks

- [x] Add an explicit clarification boundary to the authored reconciliation workflow. (AC: 1, 2)
  - [x] Update `skill_sources/auto-bean-apply/SKILL.md` and packaged prompt metadata so ambiguous or unfamiliar reconciliation outcomes stop and enter a clarification checkpoint instead of silently choosing a risky posting interpretation.
  - [x] Require the workflow to explain uncertainty using concrete evidence from reviewed `statements/parsed/` inputs, current ledger context, and current candidate postings rather than vague statements about model confidence.
  - [x] Keep the clarification path inside the existing validation-plus-diff review workflow so it augments the current trust boundary instead of creating a separate approval system.
- [x] Define a structured, reviewable clarification artifact or contract. (AC: 1, 2)
  - [x] Add or update authored references under `skill_sources/auto-bean-apply/references/` so clarification requests, user answers, resumed interpretation, and resulting reconciliation changes are captured.
  - [x] Ensure the contract distinguishes between evidence, uncertainty reasons, requested user decisions, user-provided answers, and resulting interpretation changes.
  - [x] Keep the artifact file-backed and local-first; do not rely on opaque conversational memory as the only source of truth for a resumed reconciliation decision.
- [x] Make clarification prompts targeted, bounded, and trustworthy. (AC: 1)
  - [x] Ask only the minimum set of questions needed to unblock a risky interpretation, prioritizing account choice, transfer intent, duplicate suspicion, or source-specific meaning over open-ended interrogation.
  - [x] Phrase prompts so the user can act on them: explain what the workflow observed, what candidate interpretations remain plausible, what the risk is if it guesses wrong, and what decision would let it proceed.
  - [x] Distinguish confirmed facts from inferences and avoid implying certainty when the workflow is still blocked.
- [x] Resume reconciliation from clarification without losing reviewability. (AC: 2)
  - [x] Apply the user’s clarification to the current reconciliation result and show how the answer changed account mapping, transaction interpretation, warning status, blocker status, or candidate postings.
  - [x] Preserve the before-and-after trace so the user can inspect how clarification altered the pending result before commit/push approval.
  - [x] Fail closed when the user response is still ambiguous, contradictory, or insufficient; request another bounded clarification or leave the result blocked rather than forcing an interpretation.
- [x] Prepare the clarified outcome for later governed reuse without expanding scope too early. (AC: 2)
  - [x] Update workflow guidance so reusable clarification outcomes are prepared for the governed memory path introduced in Epic 4, but do not treat this story as authorization to build the full durable-memory management workflow yet.
  - [x] Keep clarified outcomes attributable to current evidence and current user input so later reuse remains reviewable rather than becoming invisible auto-categorization.
  - [x] Avoid broad preference learning, autonomous tuning, or unrelated categorization memory in this story; keep scope limited to clarification-aware reconciliation.
- [x] Align runtime guidance, packaging, and deterministic coverage with the new clarification checkpoint. (AC: 1, 2)
  - [x] Update workspace guidance and README language only where needed so generated workspaces describe when ambiguous reconciliation results pause for clarification and how the workflow resumes safely.

## Dev Notes

- Story 3.3 builds directly on Story 3.2's conservative findings model. Transfers, duplicates, unbalanced outcomes, and currency-risk conditions are already surfaced as warnings or blockers; this story adds the user-guided path for resolving the subset that cannot be handled safely through deterministic checks alone.
- Story 3.1 and Story 2.3 established the review boundary that must remain intact here: reviewed parsed evidence, derived ledger edits, validation output, findings, and `git diff` stay visible before any commit/push approval. Clarification should strengthen that boundary, not bypass it.
- Story 2.4 introduced governed repeated-import source context, but durable reuse of clarification outcomes is still ahead in Epic 4. This story should prepare inspectable clarification data so later memory work has a clean contract to build on without prematurely implementing full memory governance.
- The product repo is not the runtime ledger workspace. Implementation here should focus on authored skill behavior, packaged references, workspace guidance, init-time materialization, smoke coverage, and deterministic tests so generated workspaces inherit the clarification workflow.
- No separate UX artifact or `project-context.md` was found. Interaction guidance therefore comes from Epic 3 wording, PRD trust requirements, architecture clarification and safety-control rules, the approved direct-mutation path, and the current Story 3.1 and 3.2 review boundary.
- The clarification workflow should stay bounded and surgical. It is meant to unblock ambiguous transaction interpretation, not to become a generic chat session or a substitute for later troubleshooting and rollback stories.

### Technical Requirements

- Keep reviewed parsed statement evidence under `statements/parsed/` and import-state tracking under `statements/import-status.yml`; clarification requests must be rooted in those artifacts plus current ledger context and current candidate postings.
- Preserve the two-step workflow split: `auto-bean-import` owns normalized intake and import-source context, while `auto-bean-apply` owns reconciliation, clarification checkpoints, direct ledger mutation review, validation interpretation, and approval-bound finalization.
- Clarification requests must be evidence-backed and actionable. The workflow should identify the ambiguous fact pattern, the plausible interpretations still on the table, and the specific user decision needed to continue safely.
- Keep clarification state reviewable and file-backed if support artifacts are introduced. Do not rely solely on prompt-history continuity for resumed reconciliation decisions that materially affect ledger outcomes.
- Treat unresolved ambiguity as a blocker. The workflow must not silently choose an account, merge or discard suspected duplicates, classify a transfer, or invent balancing postings merely because a likely guess exists.
- Keep clarified outcomes attributable to both current evidence and the specific user answer that changed the result. The resumed workflow should show what changed before it asks for final approval.
- Use Context7 Beancount documentation as the primary reference whenever the implementation needs authoritative guidance on transaction balancing, elided amounts, `open` directive currency constraints, or balance-check semantics that shape what can be clarified safely.
- If Python support code is introduced for clarification contracts or typed result structures, keep it flat and support-oriented in existing modules, and follow the repo’s Pydantic v2 expectations with `snake_case` field names.

### Architecture Compliance

- Architecture requires uncertainty management to be explicit: ambiguous interpretation must escalate to clarification instead of forcing unsafe outcomes.
- Validation, review, diff visibility, approval gating, auditability, and rollback readiness remain mandatory cross-cutting concerns. Clarification outcomes should feed the existing review package rather than branching into a separate hidden state machine.
- The architecture remains local-first and file-backed. Clarification records, if introduced, must live in governed local artifacts rather than databases, remote services, or opaque caches.
- Risky actions still require explicit user approval before accepted ledger mutation. Clarification may change the candidate result, but it does not replace commit/push approval.
- Reusable clarification outcomes should be structured so Epic 4 can persist them through the governed memory abstraction without changing the higher-level workflow boundary defined here.

### Library / Framework Requirements

- Beancount still requires transactions to balance; clarification should help the workflow arrive at a trustworthy explicit interpretation, not normalize unbalanced candidate results as acceptable output.
- Beancount can infer one missing posting amount in some cases, but this workflow should continue to prefer explicit, inspectable postings so ambiguous imports remain reviewable.
- `open` directives may restrict allowed account currencies; clarification and resumed reconciliation should treat those constraints as evidence-backed validation boundaries rather than optional hints.
- Balance checks remain useful guardrails for detecting missing or duplicated entries. Even if this story does not author new `balance` directives, clarification-aware reconciliation should stay compatible with that validation model.


### File Structure Requirements

- Likely files to create or modify when implementing this story:
  - `skill_sources/auto-bean-apply/SKILL.md`
  - `skill_sources/auto-bean-apply/agents/openai.yaml`
  - `skill_sources/auto-bean-apply/references/`
  - `skill_sources/shared/beancount-syntax-and-best-practices.md`
  - `workspace_template/AGENTS.md`
  - `README.md`
  - `src/auto_bean/init.py`
  - `src/auto_bean/smoke.py`
  - `tests/`
- Author skill behavior in `skill_sources/` first.
- Do not add live runtime skills under product-repo `.agents/skills/`.
- Materialize any new authored clarification references into the user workspace during `auto-bean init`, not by editing installed runtime copies in the product repo.

### Testing Requirements

- Run `uv run ruff check` and `uv run ruff format` after code changes.
- Run `uv run mypy` when changing Python code.
- Run `uv run pytest` when changing Python code.
- Add deterministic tests for:
  - clarification contract examples and required `snake_case` keys
  - evidence-backed clarification wording in the authored workflow
  - blocked-until-clarified behavior for ambiguous or low-confidence outcomes
  - resumed reconciliation traces that show how user input changed the result
  - packaging and workspace materialization for any new authored clarification references

### Previous Story Intelligence

- Story 3.1 established the candidate-posting workflow: reviewed parsed evidence becomes direct working-tree ledger edits only through `auto-bean-apply`, with validation, concise review context, and `git diff` before commit or push.
- Story 3.2 added conservative transfer, duplicate, and unbalanced-outcome findings plus explicit warning versus blocker status. Story 3.3 should resolve blocked ambiguous cases through clarification while keeping those findings distinct and reviewable.
- Story 2.3 already made the review surface explicit: parsed facts, derived ledger edits, validation outcome, and diff appear together before finalization. Clarification should plug into that same surface rather than inventing a parallel acceptance mode.
- Story 2.4 introduced governed repeated-import source context under `.auto-bean/memory/import_sources/`. Story 3.3 may reference that bounded context as advisory evidence, but clarified outcomes must still remain attributable to current statement facts and current user answers.

### Git Intelligence

- Recent commits: `dc858a3 story 3.2`, `c197324 nit`, `65a3ee0 nit`, `d5cabf0 wip`, `ba493df wip`.
- Recent repo activity continues to pair authored skill changes with workspace guidance, packaging updates, and deterministic coverage. Story 3.3 should follow that same product shape instead of landing as prompt-only logic with no packaged contract or validation.
- The latest Epic 3 implementation tightened wording in runtime guidance after major workflow changes. Clarification wording here should therefore be minimal, precise, and consistent with the established import/apply split.

### Latest Technical Information

- Context7 Beancount docs confirm that balanced transactions remain the core accounting rule. Clarification should therefore be used to resolve ambiguity before risky postings are treated as trustworthy results.
- The same docs also confirm that Beancount can interpolate one missing posting amount in some cases. This workflow should still prefer explicit, inspectable postings so ambiguous interpretations remain understandable to the user.
- Current Beancount docs continue to document `open` directives as the mechanism for optional account currency constraints, and validation checks those constraints against transaction postings. Clarification-aware reconciliation should treat those constraints as part of the safety boundary.
- Beancount balance checks remain a useful verification model for catching missing or duplicate ledger effects. Even without adding new balance assertions in this story, the clarification flow should preserve compatibility with that kind of validation reasoning.

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
- [Apply skill source](/Users/sam/Projects/auto-bean/skill_sources/auto-bean-apply/SKILL.md)
- [Import skill source](/Users/sam/Projects/auto-bean/skill_sources/auto-bean-import/SKILL.md)
- [Beancount syntax guidance](/Users/sam/Projects/auto-bean/skill_sources/shared/beancount-syntax-and-best-practices.md)
- [Workspace agents guide](/Users/sam/Projects/auto-bean/workspace_template/AGENTS.md)
- [README](/Users/sam/Projects/auto-bean/README.md)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Add an explicit clarification checkpoint to `auto-bean-apply` so ambiguous reconciliation outcomes stop, explain uncertainty, and request bounded user input instead of guessing.
- Define a reviewable clarification artifact or contract that records the blocking evidence, the questions asked, the user answers received, and the resumed interpretation outcome.
- Align workspace guidance, packaging, so generated workspaces consistently materialize and describe the clarification-aware reconciliation workflow.

### Debug Log References

- Story 3.3 created on 2026-04-22 from the current `epics.md`, `prd.md`, `architecture.md`, sprint change proposal dated 2026-04-12, `sprint-status.yaml`, Stories 2.3, 2.4, 3.1, and 3.2, current authored import/apply workflow docs, workspace guidance, and recent git history.
- No dedicated UX artifact or `project-context.md` was available, so interaction requirements were derived from Epic 3 wording, PRD trust requirements, architecture uncertainty-management rules, the direct-mutation workflow boundary, and the reconciliation-warning model already established in Story 3.2.
- Context7 Beancount docs were consulted to keep the story’s balancing, elided-amount, currency-constraint, and balance-check notes aligned with current Beancount guidance.
- Validation passed with `uv run ruff check`, `uv run ruff format`, `uv run mypy`, `uv run pytest`, and `uv run python scripts/run_smoke_checks.py`.
- Simplified the clarification approach after user feedback: keep a guidance reference, ask the user directly when blocked, then adjust the drafted changes instead of introducing a separate clarification artifact or record.

### Completion Notes List

- Selected the first backlog story in sprint order: `3-3-run-clarification-workflows-for-ambiguous-or-unfamiliar-transaction-patterns`.
- Added a clarification checkpoint to the authored `auto-bean-apply` workflow and packaged prompt metadata so ambiguous or unfamiliar reconciliation outcomes pause before any risky interpretation is applied.
- Added a lightweight clarification guidance reference under `skill_sources/auto-bean-apply/references/` so the agent reads the guidance, asks the user directly, adjusts drafted changes based on the answer, and suggests a source-context memory update when the clarified rule is narrowly reusable.
- Updated shared Beancount guidance, workspace instructions, and README language so generated workspaces describe the simpler clarification checkpoint and resumed result consistently.
- Added deterministic coverage for clarification guidance packaging, authored workflow wording, simplified resume behavior, and smoke checks for the new reference.
- Kept Story 3.3 focused on clarification-aware reconciliation rather than letting it sprawl into troubleshooting, rollback orchestration, or full governed-memory management.
- Preserved the current trust model: ambiguous results stay blocked until clarified, resumed outcomes remain reviewable, and commit/push approval remains the final acceptance boundary.

### File List

- _bmad-output/implementation-artifacts/3-3-run-clarification-workflows-for-ambiguous-or-unfamiliar-transaction-patterns.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- README.md
- skill_sources/auto-bean-apply/SKILL.md
- skill_sources/auto-bean-apply/agents/openai.yaml
- skill_sources/auto-bean-apply/references/clarification-guidance.md
- skill_sources/shared/beancount-syntax-and-best-practices.md
- src/auto_bean/init.py
- src/auto_bean/smoke.py
- tests/test_apply_skill_assets.py
- tests/test_init.py
- workspace_template/AGENTS.md

### Change Log

- 2026-04-22: Implemented the clarification-aware reconciliation checkpoint, simplified it to direct user clarification guided by a reference file, updated packaging and workspace guidance, and validated the new coverage.
