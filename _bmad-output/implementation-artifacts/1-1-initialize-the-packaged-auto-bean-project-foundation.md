# Story 1.1: Initialize the packaged auto-bean project foundation

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a solo personal-finance user,
I want the project initialized with the packaged `uv` application foundation,
so that the repo starts from a reproducible, maintainable base that matches the architecture.

## Acceptance Criteria

1. Given an empty or pre-bootstrap product repo, when the initialization workflow is run, then the project is initialized using `uv init --package auto-bean` or an equivalent resulting packaged structure, and the repo contains the expected packaged Python foundation, including `pyproject.toml`, `src/`, and a baseline project entrypoint.
2. Given the packaged foundation exists, when a developer inspects the repo structure, then stable user-owned assets and evolving tool logic are separated clearly, and the structure leaves room for skills, scripts, governed memory, and artifact directories without overwriting ledger assets.

## Tasks / Subtasks

- [x] Run the starter initialization for the product repo using `uv init --package auto-bean` or produce the same packaged result intentionally. (AC: 1)
- [x] Confirm the generated package identity is `auto_bean` under `src/` and that the repo has a baseline importable entrypoint. (AC: 1)
- [x] Preserve existing planning artifacts and repo metadata while adding only the minimum packaged-app foundation files required for the first implementation slice. (AC: 1, 2)
- [x] Establish the initial source layout using architecture-approved layer boundaries:
  - [x] `src/auto_bean/cli/`
  - [x] `src/auto_bean/application/`
  - [x] `src/auto_bean/domain/`
  - [x] `src/auto_bean/infrastructure/`
  - [x] `src/auto_bean/memory/`
  - [x] `tests/`
  (AC: 2)
- [x] Ensure repo-level structure keeps room for governed user-owned state and helper surfaces without creating them prematurely:
  - [x] Reserve top-level roles for `scripts/`, `.agents/skills/`, and future `.auto-bean/` state
  - [x] Do not place ledger, memory, or artifact files inside `src/`
  (AC: 2)
- [x] Add or update minimal documentation so a future maintainer can see that this story establishes the packaged foundation only, not full bootstrap/readiness flows. (AC: 2)
- [x] Add baseline automated verification for this initial foundation:
  - [x] a smoke test or equivalent assertion that the package imports / entrypoint resolves
  - [x] test placement under `tests/`
  (AC: 1)

## Dev Notes

- This repo currently contains planning artifacts plus a minimal [README](/Users/sam/Projects/auto-bean/README.md); there is no existing Python application tree yet. Treat this as a greenfield packaged-foundation story, not a refactor.
- Keep scope narrow. Story 1.1 creates the packaged application baseline only. Dependency bootstrap, readiness verification, CI baseline, and ledger workspace creation are covered by later stories.
- The architecture explicitly calls out this story as the first implementation step in the delivery sequence. Do not skip to workflow or ledger features in this story.

### Project Structure Notes

- Use a packaged `src/` layout. The architecture selected `uv` specifically because `uv init --package` creates a `src`-based structure appropriate for CLI-oriented Python projects and future distribution.
- Use `snake_case` for Python package and file names. The package directory should be `src/auto_bean/`, not `src/auto-bean/`.
- Organize code by layer, not by ad hoc utilities. The intended initial directories are:
  - `src/auto_bean/cli/` for command entrypoints only
  - `src/auto_bean/application/` for workflow services/orchestration
  - `src/auto_bean/domain/` for models, policies, and domain errors
  - `src/auto_bean/infrastructure/` for filesystem/git/Beancount/Fava/external adapters
  - `src/auto_bean/memory/` for memory schemas and file-backed persistence code
  - `tests/` for test suites
- Keep stable user-owned assets separate from evolving tool logic:
  - future durable memory belongs under `.auto-bean/memory/`
  - future artifacts belong under `.auto-bean/artifacts/`
  - `ledger.beancount` remains a stable user-owned workspace entrypoint later
  - none of those durable assets should live inside `src/`
- Do not create a generic `utils` dumping ground. Shared helpers must live in the narrowest responsible layer.

### Developer Guardrails

- Do not introduce a public API surface. MVP is CLI-and-skill first; internal Python services and commands are the intended interfaces.
- CLI code may parse input and render output, but it must not contain business logic. Keep the package foundation aligned with later service-boundary work.
- Preserve repo-local planning outputs under `_bmad-output/`; initialization should not overwrite or relocate them.
- Avoid creating ledger, memory, or artifact content in this story beyond directory-safe structure decisions. This story is about foundation, not operational state.
- Leave clear room for `.agents/skills/**/scripts/` and top-level `scripts/` because skills remain a first-class user-facing surface.

### Library / Framework Requirements

- Preferred initializer: `uv init --package auto-bean`.
- `uv` remains the chosen project/runtime/package manager because it supports the local-first, lightweight bootstrap model and packaged `src` layout.
- Architecture notes say Typer, pytest, and Ruff are expected follow-on choices. For this story:
  - pytest should be used for baseline verification if tests are added now
  - Ruff can be introduced if needed to keep the initial foundation aligned with the later CI baseline
  - Typer may be deferred unless the entrypoint implementation benefits from establishing the CLI module shape now
- Use Pydantic v2 later at service boundaries; do not add speculative models here unless the package foundation needs a minimal placeholder.
- Latest official tooling context:
  - Astral's `uv` CLI docs continue to document `uv init` as the project creation command and `--build-backend` implicitly sets `--package`.
  - The latest official `uv` GitHub release visible during story creation is `0.9.21` on 2025-12-30. The story should target current `uv` behavior, not older pre-`0.9` assumptions.

### Testing Requirements

- Add at least one automated check that proves the packaged foundation is valid enough for future stories to build on.
- Place tests under top-level `tests/`.
- Keep test names and fixtures deterministic. Architecture requires deterministic workflow verification over time, and this story should avoid introducing flaky foundations.
- If a CLI entrypoint is introduced, test the module/import boundary rather than implementing broad workflow behavior early.

### Git Intelligence Summary

- Recent repo history is planning-heavy and matches the current state:
  - `43daf40` `sprint planning`
  - `784b4c5` `correct course`
  - `3f04ddd` `readiness`
  - `3df80ff` `epics and stories`
  - `15e5ce0` `architecture`
- There is no earlier implementation story in this epic, so there are no previous-story learnings to inherit yet.

### Project Context Reference

- No `project-context.md` file was found in the repository.
- No standalone UX artifact was found. For this story, trust-sensitive UX requirements are not directly in scope, but future stories will need explicit interaction details for review, approval, and troubleshooting flows.

### References

- [Epic breakdown](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/epics.md) - `Epic 1`, `Story 1.1`, and neighboring Epic 1 stories for scope boundaries.
- [Architecture](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/architecture.md) - `Starter Template Evaluation`, `Selected Starter: uv Packaged Application`, `Infrastructure & Deployment`, `Workflow Verification & Observability Contract`, `Structure Patterns`, and `Recommended pattern`.
- [PRD](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/prd.md) - `Executive Summary`, `Technical Success`, `Developer Tool Specific Requirements`, and `MVP Feature Set`.
- [Implementation readiness report](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/implementation-readiness-report-2026-03-31.md) - notes that Story 1.1 is valid but should remain narrowly scoped.
- [uv CLI reference](https://docs.astral.sh/uv/reference/cli/) - official `uv init` behavior and packaged-project flags.
- [uv releases](https://github.com/astral-sh/uv/releases) - latest official release observed during story creation.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story created from BMAD planning and architecture artifacts on 2026-03-31.
- Verified the `uv` packaged template in a scratch directory, then reproduced the equivalent packaged foundation intentionally in-repo to preserve the existing README and planning outputs.
- Red phase: `pytest tests/test_package_foundation.py` failed before `src/auto_bean/` existed.
- Green phase: `pytest` passed after adding the packaged layout, entrypoint, and pytest configuration.
- Verified module entrypoint with `PYTHONPATH=src python3 -m auto_bean`.

### Implementation Plan

- Reproduce the minimal `uv init --package auto-bean` result intentionally instead of running it directly in the repo, so existing repo metadata and docs remain intact.
- Create only the packaged Python baseline and architecture-approved layer directories required by Story 1.1.
- Add a deterministic smoke test under `tests/` that validates the package layout and importable entrypoint.
- Document repo boundaries so future runtime state stays outside `src/`.

### Completion Notes List

- Comprehensive story context created for the first backlog item auto-discovered from sprint status.
- No prior implementation story or project-context artifact existed.
- Story guidance intentionally keeps Story 1.1 narrow so later setup/readiness stories retain their own scope.
- Added a minimal packaged Python application foundation with `pyproject.toml`, `.python-version`, `src/auto_bean/`, and a baseline CLI/module entrypoint.
- Established the initial layer package layout for `cli`, `application`, `domain`, `infrastructure`, and `memory`, with test coverage under `tests/`.
- Updated the README to document that user-owned ledger and governed runtime state stay outside `src/`, while reserving top-level roles for `scripts/`, `.agents/skills/`, and future `.auto-bean/` state.
- Validation completed with `pytest` and `PYTHONPATH=src python3 -m auto_bean`.

### File List

- _bmad-output/implementation-artifacts/1-1-initialize-the-packaged-auto-bean-project-foundation.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- .python-version
- README.md
- pyproject.toml
- src/auto_bean/__init__.py
- src/auto_bean/__main__.py
- src/auto_bean/application/__init__.py
- src/auto_bean/cli/__init__.py
- src/auto_bean/cli/main.py
- src/auto_bean/domain/__init__.py
- src/auto_bean/infrastructure/__init__.py
- src/auto_bean/memory/__init__.py
- tests/test_package_foundation.py

### Change Log

- 2026-03-31: Added the initial packaged `auto_bean` foundation, architecture-aligned layer packages, baseline entrypoint, README boundary notes, and smoke-test coverage for Story 1.1.
