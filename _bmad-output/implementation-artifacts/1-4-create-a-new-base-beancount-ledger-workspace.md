# Story 1.4: Create a new base Beancount ledger workspace

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a first-time user,
I want the agent to create a usable base ledger workspace,
so that I can start operating a linked personal-finance ledger without manual file scaffolding.

## Acceptance Criteria

1. Given the `auto-bean` tool is installed and the user provides a project name, when the `auto-bean init <PROJECT-NAME>` workflow is run, then the system creates a new workspace and the base Beancount ledger entrypoint with the minimum supporting files required for operation, and the created workspace is compatible with validation and Fava inspection.
2. Given the base ledger workspace has been created, when the user reviews the proposed structure, then the user can inspect what was created before risky structural changes are finalized, and the resulting ledger workspace supports later imports into the same linked ledger.

## Tasks / Subtasks

- [x] Replace the placeholder `init` implementation with a real workspace-initialization workflow. (AC: 1, 2)
  - [x] Keep `src/auto_bean/cli/main.py` thin: parse `project_name`, call the application service, and render the structured result or JSON output.
  - [x] Extend `src/auto_bean/application/setup.py` with an interactive `init()` orchestration path that validates inputs, computes the target workspace path, asks any required setup questions, records workflow events, and reuses the Story 1.3 structured artifact contract instead of inventing a second result shape.
  - [x] Include an explicit init-time question asking which coding agent the user wants to use, but support only `Codex` for now and fail clearly if another choice is requested before support exists.
  - [x] Add stable, typed init-specific domain/result models in `src/auto_bean/domain/` only if the current setup models become too overloaded; prefer extending the existing workflow result/check/event pattern first.
  - [x] Fail closed when the requested target directory already exists and is non-empty, the project name is unsafe, or required template assets are missing.
- [x] Introduce the minimum viable authored workspace template in the product repo. (AC: 1)
  - [x] Add `workspace_template/` as the source-of-truth scaffold for a fresh user ledger repo.
  - [x] Include a stable `ledger.beancount` entrypoint, an `AGENTS.md` file, and the minimum directory structure the workspace needs for a usable runtime repo: `beancount/`, `statements/raw/`, `docs/`, `.auto-bean/`, and `.agents/skills/`.
  - [x] Keep the scaffold intentionally minimal and reviewable: create empty or placeholder directories/files only where they establish required runtime boundaries for later stories.
  - [x] Install the initial skill surface under `.agents/skills/` in the generated workspace rather than `.agents/plugins/`.
  - [x] Do not fabricate full import, memory, review, or query workflows that do not exist in the product repo yet; only create the structure needed to support them later.
- [x] Make the generated workspace Beancount- and Fava-ready from day one. (AC: 1)
  - [x] Ensure `ledger.beancount` is the canonical entrypoint and references the initial ledger layout in a way that can grow into later imports.
  - [x] Add the minimum helper assets needed for validation and inspection, such as a validation helper and Fava launcher script or equivalent documented commands rooted in `ledger.beancount`.
  - [x] Run Beancount validation against the generated entrypoint as part of the init workflow and fail the workflow if the scaffold itself is invalid.
  - [x] Keep all generated runtime state inside the new workspace, not the product repo.
- [x] Produce inspectable structure output for trust and later review workflows. (AC: 2)
  - [x] Include a created-file manifest and validation summary in the structured workflow result and persisted artifact.
  - [x] Render human-readable output that tells the user where the workspace was created, which key files were generated, and how to validate or inspect it next.
  - [x] Preserve a boundary between “workspace created” and later “risky structural edits require approval”; Story 1.4 should surface what happened clearly without pre-implementing Story 1.5 approval flows.
- [x] Add deterministic automated coverage for the new initialization path. (AC: 1, 2)
  - [x] Add tests for successful workspace creation into a temp directory, including assertions on the generated file tree and `ledger.beancount` entrypoint.
  - [x] Add tests for blocked paths such as unsafe project names, pre-existing destination contents, and missing template assets.
  - [x] Add tests that the init result persists a governed artifact and includes the created-file manifest plus validation outcome.
  - [x] Extend smoke coverage so the previously blocked `init` path now exercises a successful initialization flow and at least one fail-closed path.
- [x] Update maintainer-facing docs to match the new workflow. (AC: 1, 2)
  - [x] Update `README.md` with the now-supported `auto-bean init <PROJECT-NAME>` workflow, expected output, and how to validate/open the generated workspace.
  - [x] Document the product-repo vs user-ledger-repo distinction so maintainers do not accidentally write runtime assets back into the product repo.

## Dev Notes

- Story 1.2 explicitly reserved `auto-bean init <PROJECT-NAME>` for this story, and Story 1.3 established the structured workflow-result and artifact contract that Story 1.4 should reuse.
- This is the first story that creates the runtime user ledger repo. The product repo remains the authored source of truth for code, templates, and future skill sources; the generated workspace is a separate operating repo.
- The init flow should be interactive rather than one-shot only. It needs to ask the user for required setup choices during workspace creation, including the coding-agent selection.
- The architecture expects `workspace_template/` to own the skeleton of a fresh ledger repo and `ledger.beancount` to be the stable entrypoint for validation and Fava.
- The generated workspace should also include an `AGENTS.md` file as part of the initial scaffold.
- No UX design artifact exists. Trust must therefore come from explicit CLI output, inspectable artifacts, and a workspace layout that is easy to review in ordinary files.
- For now, the coding-agent choice should be captured explicitly but only `Codex` is supported.
- Skills should be materialized into `.agents/skills/` in the generated workspace. Do not add plugin-oriented scaffolding for this story.
- The current repo does not yet contain `skill_sources/` or installed runtime skills. Story 1.4 should not invent large placeholder workflow catalogs just to match a future-state tree; keep the scaffold minimal and honest.

### Project Structure Notes

- Keep command parsing and user-facing output in `src/auto_bean/cli/`.
- Keep initialization orchestration, manifest assembly, and validation flow in `src/auto_bean/application/`.
- Keep template-copying, filesystem writes, path safety checks, and external command execution in `src/auto_bean/infrastructure/`.
- Keep reusable result models, diagnostics, created-file metadata, and error classification in `src/auto_bean/domain/`.
- Add authored runtime scaffold assets under `workspace_template/`; do not build them inline in Python string literals when file assets can be versioned directly.
- Generated runtime files belong in the created user workspace, especially `AGENTS.md` plus content under `.auto-bean/`, `beancount/`, `statements/`, `docs/`, and `.agents/`.
- Installed skill files for the workspace belong under `.agents/skills/`.

### Developer Guardrails

- Reuse the Story 1.3 workflow artifact contract. `init` should emit `run_id`, ordered events, explicit error codes, and a governed artifact instead of bespoke printing logic.
- The init flow must support interactive prompting for required choices. Do not hardcode all defaults silently when a trust-relevant choice should be surfaced to the user.
- Do not write any generated workspace files into the product repo. `auto-bean init my-ledger` should create a sibling/child workspace rooted at the requested target path.
- Treat project-name and target-path validation as a trust boundary. Reject dangerous names, path traversal, and non-empty destinations rather than trying to merge into unknown state.
- Keep `workspace_template/` as the single source of truth for scaffold contents. Avoid scattering file templates across tests, docs, and Python functions.
- Keep the scaffold intentionally small. Do not add fake importers, fake memory payloads, or speculative review systems just to fill out directories.
- Ask which coding agent the user wants to use during init, but allow only `Codex` initially and report unsupported selections clearly.
- Create `AGENTS.md` as part of the initial workspace scaffold so agent-facing operating guidance lives in the generated repo from day one.
- Make the generated ledger valid from the start. A freshly created workspace should pass Beancount validation on its base entrypoint before the workflow reports success.
- Preserve the architecture boundary that later risky ledger mutations go through proposal/review/approval flows. Story 1.4 may report created structure, but it must not silently establish future mutation shortcuts.

### Testing Requirements

- Keep all existing readiness, diagnostics, and smoke tests green.
- Add deterministic coverage for:
  - successful `auto-bean init <PROJECT-NAME>` workspace creation
  - presence and expected placement of `AGENTS.md` in the generated workspace
  - interactive prompting behavior for required init questions, including coding-agent selection
  - acceptance of `Codex` and fail-closed handling for unsupported agent choices
  - fail-closed behavior for invalid names and pre-existing destinations
  - generated Beancount validation success for the base `ledger.beancount`
  - governed artifact emission with created-path manifest and validation details
  - CLI JSON and human-readable output for both success and blocked init runs
- Prefer temp-directory tests and fixture-driven assertions over writing to real user paths.
- Keep the init smoke path bounded and non-interactive so CI remains deterministic.

### Previous Story Intelligence

- Story 1.2 deliberately stopped at installing and verifying the `auto-bean` tool; it did not create a workspace, ledger, or `.auto-bean/` tree.
- Story 1.3 added the stable workflow result envelope, governed artifact persistence, smoke-check structure, and explicit error classification. Story 1.4 should build directly on those conventions.
- Recent implementation work concentrated changes in `README.md`, `src/auto_bean/application/setup.py`, `src/auto_bean/cli/main.py`, `src/auto_bean/domain/setup.py`, `src/auto_bean/infrastructure/setup.py`, and test modules under `tests/`. Expect Story 1.4 to extend those surfaces and add `workspace_template/` plus installed workspace skills under `.agents/skills/`.

### Git Intelligence

- Recent commits (`03ba6e0`, `99f9f99`, `fb3131c`) moved the story artifact, sprint tracker, docs, source modules, and tests together. Keep that pattern so the runtime initialization contract, its tests, and maintainer documentation evolve in sync.
- The repo is still clean and relatively small. This is a good time to establish `workspace_template/` cleanly rather than retrofitting scattered generated-file conventions later.

### Latest Technical Information

- `fava ledger.beancount` remains the standard launch shape for inspecting a ledger through Fava, so the generated workspace should keep `ledger.beancount` as the stable top-level entrypoint and point any helper scripts at that file. Source: [Fava Getting Started](https://beancount.github.io/fava/usage.html)
- `bean-check /path/to/file.beancount` remains the standard Beancount validation command, so Story 1.4 should validate the generated base ledger before reporting init success. Source: [Getting Started with Beancount](https://beancount.github.io/docs/getting_started_with_beancount.html), [Running Beancount & Generating Reports](https://beancount.github.io/docs/running_beancount_and_generating_reports.html)
- The current product already declares `beancount` and `fava` as runtime dependencies in `pyproject.toml`, which means Story 1.4 should build on those package-level dependencies instead of introducing a second installation mechanism for ledger validation or inspection.
- This story should establish a template-driven workspace boundary and materialize skills into `.agents/skills/` rather than introducing plugin scaffolding or generating ad hoc files directly from CLI code.

### References

- [Epic breakdown](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/epics.md)
- [Architecture](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/architecture.md)
- [PRD](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/prd.md)
- [Previous story](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/1-3-establish-the-ci-workflow-verification-and-diagnostics-baseline.md)
- [Story 1.2](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/1-2-bootstrap-local-dependencies-and-readiness-checks-on-macos.md)
- [Sprint status](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/sprint-status.yaml)
- [README](/Users/sam/Projects/auto-bean/README.md)
- [CLI entrypoint](/Users/sam/Projects/auto-bean/src/auto_bean/cli/main.py)
- [Setup service](/Users/sam/Projects/auto-bean/src/auto_bean/application/setup.py)
- [Setup infrastructure](/Users/sam/Projects/auto-bean/src/auto_bean/infrastructure/setup.py)
- [Pyproject](/Users/sam/Projects/auto-bean/pyproject.toml)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story 1.4 created on 2026-04-03 from the first backlog story in `sprint-status.yaml`.
- Context synthesized from Epic 1, the PRD, the architecture document, Stories 1.2 and 1.3, the current CLI/setup implementation, current tests, and recent git history.
- Story scope tightened to the minimum viable runtime workspace because the repo does not yet contain `skill_sources/` or installed runtime skills to materialize fully.
- Story updated with user clarification that init must be interactive, must ask for coding-agent choice, and must install skills under `.agents/skills/` instead of `.agents/plugins/`.

### Implementation Plan

- Replace the placeholder `init` workflow with a real scaffold-and-validate path that reuses the existing structured result and artifact system.
- Add `workspace_template/` as the versioned source of truth for generated runtime files and directories, including installed workspace skills under `.agents/skills/`.
- Include `AGENTS.md` in the generated workspace scaffold alongside the ledger entrypoint and installed skills.
- Add the interactive init question flow, including supported coding-agent selection with `Codex` as the only valid option for now.
- Validate the generated `ledger.beancount` and persist a created-file manifest so the new workspace is immediately inspectable and trustworthy.
- Expand tests, smoke checks, and maintainer docs so the init workflow is covered as a first-class supported path.

### Completion Notes List

- Implemented the interactive `auto-bean init <PROJECT-NAME>` workflow with structured checks, governed artifact persistence, sibling-workspace targeting when run from the product repo, and fail-closed validation for unsafe names, unsupported coding agents, non-empty targets, missing templates, and invalid generated ledgers.
- Added the authored `workspace_template/` scaffold with `ledger.beancount`, `AGENTS.md`, minimal runtime directories, a small `.agents/skills/` surface, and helper scripts for validation and Fava inspection in generated workspaces.
- Expanded deterministic coverage for init success, blocked cases, artifact contents, CLI rendering, smoke checks, and maintainer documentation.

### File List

- README.md
- _bmad-output/implementation-artifacts/1-4-create-a-new-base-beancount-ledger-workspace.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- src/auto_bean/application/setup.py
- src/auto_bean/application/smoke.py
- src/auto_bean/cli/main.py
- src/auto_bean/domain/setup.py
- src/auto_bean/infrastructure/setup.py
- tests/test_package_foundation.py
- tests/test_setup_diagnostics.py
- tests/test_smoke_checks.py
- workspace_template/AGENTS.md
- workspace_template/ledger.beancount
- workspace_template/beancount/opening-balances.beancount
- workspace_template/docs/README.md
- workspace_template/.agents/skills/README.md
- workspace_template/.auto-bean/.gitkeep
- workspace_template/statements/raw/.gitkeep

### Change Log

- 2026-04-03: Implemented the Story 1.4 init workflow, added the authored workspace template, expanded CLI/test coverage, and updated maintainer documentation.

### Review Findings

- [x] [Review][Patch] Failed init leaves a partially created workspace behind and blocks reruns [src/auto_bean/application/setup.py:239]
- [x] [Review][Patch] Generated workspace guide points users at commands that are not installed on PATH [workspace_template/docs/README.md:5]
- [x] [Review][Patch] Initialized workspace should start as a Git repository [src/auto_bean/application/setup.py:295]
