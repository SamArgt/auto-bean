# Story 1.2: Bootstrap local dependencies and readiness checks on macOS

Status: in-progress

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a new user on a supported macOS machine,
I want auto-bean to install or verify its required local tooling,
so that I can tell whether my environment is ready before attempting ledger work.

## Acceptance Criteria

1. Given a supported macOS environment, when the bootstrap workflow is run, then it installs or verifies the required local dependencies for auto-bean, Beancount, and Fava, and it reports any missing prerequisites with clear remediation guidance.
2. Given the environment bootstrap has completed, when the readiness check is run, then the system verifies that required commands, configuration, and local runtime dependencies are available, returns a clear pass/fail result before any ledger operation begins, and completes successfully within 2 minutes on an already bootstrapped supported environment.

## Tasks / Subtasks

- [x] Add a CLI surface for environment setup and verification without burying logic in the command layer. (AC: 1, 2)
  - [x] Extend the existing `auto_bean` entrypoint with explicit bootstrap/readiness commands or subcommands.
  - [x] Keep terminal rendering in `src/auto_bean/cli/` and move orchestration into `src/auto_bean/application/`.
- [x] Introduce typed result models for bootstrap and readiness outcomes. (AC: 1, 2)
  - [x] Use explicit status/result objects with stable `snake_case` fields such as `status`, `error_code`, `message`, `details`, and any timing metadata needed for readiness reporting.
  - [x] Keep those models ready to support later structured diagnostics and artifact persistence in Story 1.3 without requiring a redesign.
- [x] Implement the macOS bootstrap workflow in the product repo. (AC: 1)
  - [x] Detect whether the current machine is a supported macOS environment and fail fast with a clear unsupported-environment message otherwise.
  - [x] Install or verify project-managed Python dependencies through the repo's `uv` workflow instead of using `sudo pip`, Homebrew-only assumptions, or ad hoc global mutation.
  - [x] Ensure the workflow covers the auto-bean package itself plus required local dependencies for Beancount and Fava.
  - [x] Provide remediation guidance when prerequisites are missing, installation fails, or a dependency is present but unusable.
- [x] Implement a readiness check that is safe to run before any ledger workflow. (AC: 2)
  - [x] Verify required commands and runtime dependencies that the current stories actually depend on, including the package entrypoint and the installed Beancount/Fava tooling.
  - [x] Verify required project-local configuration that exists at this stage, such as the `uv`-managed environment and installable package state, without inventing future ledger-workspace requirements early.
  - [x] Return a clear pass/fail summary that a later skill or CLI workflow can gate on before ledger-changing work begins.
  - [x] Keep the re-run path lightweight enough that a successful readiness check on an already bootstrapped setup remains under the 2-minute target.
- [x] Add deterministic automated coverage for both happy-path and blocked-path behavior. (AC: 1, 2)
  - [x] Add tests for unsupported OS detection, missing prerequisite reporting, and successful readiness verification.
  - [x] Preserve and extend the existing foundation tests from Story 1.1 instead of replacing them.
  - [x] Prefer smoke/integration coverage that exercises the command surface through `uv run` or the equivalent installed project environment.
- [x] Add maintainer-facing documentation for bootstrap and readiness usage. (AC: 1, 2)
  - [x] Document the supported macOS-only scope, expected commands, and remediation behavior.
  - [x] Keep the docs focused on product-repo bootstrap and readiness only; full first-use quickstart remains Story 1.6 scope.

### Review Findings

- [ ] [Review][Patch] Documented `uv run` entrypoints bypass the bootstrap/readiness contract [README.md:17]
- [x] [Review][Patch] Declared dependency validation rejects valid version-pinned requirements [src/auto_bean/application/setup.py:185]
- [x] [Review][Patch] Bootstrap still runs `uv sync` after a failed dependency precheck [src/auto_bean/application/setup.py:50]
- [x] [Review][Patch] Invalid `pyproject.toml` content crashes the command instead of returning diagnostics [src/auto_bean/application/setup.py:186]

## Dev Notes

- Story 1.1 already established the packaged `uv` application skeleton and the layer directories under `src/auto_bean/`. Build on that structure instead of creating standalone scripts with duplicated logic.
- This story is about making the product repo installable and self-checking on supported macOS machines. It is not yet the story for creating a user ledger repo, installing runtime skills into a ledger workspace, or scaffolding ledger files.
- The acceptance criteria require two distinct but related capabilities:
  - bootstrap: install or verify dependencies and explain remediation
  - readiness: confirm the environment is usable before later ledger operations start
- The architecture treats setup and environment checks as a setup/orchestration layer. Implement this as reusable services with a thin CLI wrapper, not as a CLI-only shell script with opaque side effects.

### Project Structure Notes

- Keep command parsing and user-facing output in `src/auto_bean/cli/`.
- Put workflow orchestration for bootstrap/readiness under `src/auto_bean/application/`.
- Put OS inspection, subprocess execution, dependency probing, and tool-specific integration helpers under `src/auto_bean/infrastructure/`.
- Keep domain-neutral result models and shared enums/errors in `src/auto_bean/domain/` if the implementation needs them.
- Do not place runtime ledger data, memory files, or artifacts under `src/`.
- The architecture's recommended product-repo structure explicitly reserves top-level `scripts/bootstrap.sh` for repo helper tooling. If a shell helper is useful, keep it as a thin convenience wrapper over the Python service/CLI path rather than the main source of truth.
- Do not introduce live installed skills under `.agents/skills/` in the product repo. Story 1.2 is still product-repo work.

### Developer Guardrails

- Fail closed on unsupported environments. V1 is macOS-only; do not silently claim support for Linux or Windows.
- Avoid global system mutation when a project-managed `uv` flow is sufficient. The story should not depend on `sudo` installs or mutate system Python.
- Do not invent future workspace checks too early. Readiness in this story should validate the current product-repo environment, not require `ledger.beancount`, `.auto-bean/`, or installed runtime skills that do not exist yet.
- Keep bootstrap idempotent. Re-running it on an already prepared repo should verify and reconcile state, not duplicate work or corrupt the environment.
- Keep readiness side-effect-light. A readiness command should primarily inspect and report; it should not perform risky ledger changes.
- Result output should be explicit and machine-friendly enough for later automation. Use stable status naming and avoid vague free-form-only success messages.
- Preserve Story 1.1 boundaries and keep the current packaged foundation working while expanding the command surface.

### Library / Framework Requirements

- Continue using `uv` as the project/runtime/package manager. This matches the selected architecture and the existing repo foundation.
- Use `uv` project workflows for dependency management and execution. Official `uv` docs currently describe `uv sync` for syncing the environment and note that `uv run` keeps the lockfile and environment in sync automatically.
- Required dependency scope for this story:
  - the installable `auto-bean` package itself
  - Beancount as a required local dependency
  - Fava as a required local dependency
- Architecture guidance still points to Typer as the likely CLI framework and pytest as the expected test framework. Introducing Typer here is reasonable if it materially improves the bootstrap/readiness command surface, but avoid broad framework churn that is not needed for this story.
- As of 2026-03-31, the latest official PyPI releases observed during story creation were:
  - `beancount 3.2.0` with Python `>=3.9` and macOS 11+ ARM64 wheel support listed on PyPI
  - `fava 1.30.12` with Python `>=3.10` support listed on PyPI
- Those observed releases are compatible with the current project requirement `requires-python = ">=3.13"` in `pyproject.toml`. Treat that as validation for project-managed dependency installation, not as a mandate to hard-code exact pins unless the implementation chooses to lock them through normal `uv` workflows.
- Beancount's official install docs warn against relying on `sudo pip` as the default installation path. Keep installation guidance inside the repo's managed environment instead.

### Testing Requirements

- Keep the existing `tests/test_package_foundation.py` green.
- Add deterministic tests for:
  - supported vs unsupported OS detection
  - missing dependency/prerequisite reporting
  - successful bootstrap verification on an already prepared environment
  - clear pass/fail readiness output
- Prefer fast unit tests around detection/result-building logic plus at least one smoke-oriented test that exercises the command surface.
- Keep the happy-path readiness check comfortably under the 2-minute target on a bootstrapped environment; automated tests should verify the logic without depending on slow network-heavy installs where possible.
- Story 1.3 will formalize CI and artifact conventions, but Story 1.2 tests should already avoid flaky timing assumptions and opaque manual verification.

### Previous Story Intelligence

- Story 1.1 intentionally kept scope narrow and established only the packaged foundation. Reuse its existing package boundaries instead of relocating code or reworking the repo layout.
- Story 1.1 created:
  - `pyproject.toml` with `requires-python = ">=3.13"`
  - `src/auto_bean/` with `cli`, `application`, `domain`, `infrastructure`, and `memory` packages
  - a simple `auto_bean` entrypoint through `src/auto_bean/cli/main.py`
  - baseline pytest configuration and a smoke test under `tests/`
- The Story 1.1 completion notes explicitly deferred bootstrap/readiness flows to later stories. Implement them now, but do not retroactively widen Story 1.1 by restructuring unrelated files.

### Git Intelligence Summary

- Recent commits show the first implementation slice is complete and tracked cleanly:
  - `bed322d` created story 1.1
  - `af5974f` implemented story 1.1
  - `2d90c8b` marked story 1.1 done
- The implementation commit touched `pyproject.toml`, `README.md`, `src/auto_bean/**`, and `tests/test_package_foundation.py`. Those are the natural starting points for Story 1.2 as well.
- Current worktree was clean during story creation, so there were no conflicting local changes to account for.

### Latest Technical Information

- Official `uv` project documentation currently states that packaged apps created with `uv init --package` use a `src/` layout and a build system, which matches the current repo.
- Official `uv` sync/run documentation currently states that:
  - `uv sync` explicitly syncs the project environment from the lockfile
  - `uv run` automatically checks/updates the lockfile and environment before executing commands
- That means the safest Story 1.2 implementation should treat the repo's `uv` environment as the primary installation target and verification surface rather than relying on unmanaged global packages.
- Official PyPI metadata observed on 2026-03-31 shows current stable releases for the two required local dependencies:
  - Beancount `3.2.0`
  - Fava `1.30.12`
- Fava's current PyPI instructions still present the basic run pattern as `fava ledger.beancount`; keep that in mind when deciding what command availability the readiness check should verify, even though ledger creation itself belongs to Story 1.4.

### Project Context Reference

- No `project-context.md` file was found in the repository.
- No standalone UX artifact was found. For this story, terminal UX should still be deliberate: concise pass/fail reporting, visible remediation steps, and no ambiguous "maybe ready" output.

### References

- [Epic breakdown](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/epics.md) - `Epic 1`, `Story 1.2`, and neighboring Epic 1 stories for scope boundaries.
- [Architecture](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/architecture.md) - `Selected Starter: uv Packaged Application`, `Workflow Verification & Observability Contract`, `Structure Patterns`, `Product Repo Structure`, `Product Repo Boundaries`, `Runtime Boundaries`, and `Implementation Handoff`.
- [PRD](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/prd.md) - FR1, FR3, FR4, FR51, measurable readiness targets, and the local-first bootstrap requirements.
- [Implementation readiness report](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/implementation-readiness-report-2026-03-31.md) - confirms Story 1.2 covers the dependency-installation and readiness requirements.
- [Previous story](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/1-1-initialize-the-packaged-auto-bean-project-foundation.md) - packaged foundation boundaries and existing repo conventions.
- [uv creating projects](https://docs.astral.sh/uv/concepts/projects/init/) - current packaged-app `uv init --package` structure and build-system behavior.
- [uv locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/) - current `uv sync` and `uv run` environment-management behavior.
- [beancount PyPI](https://pypi.org/project/beancount/) - current stable release metadata observed during story creation.
- [fava PyPI](https://pypi.org/project/fava/) - current stable release metadata and command usage observed during story creation.
- [Beancount install docs](https://beancount.github.io/docs/installing_beancount.html) - caution against defaulting to global `sudo pip` installation guidance.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story created from BMAD planning and architecture artifacts on 2026-03-31.
- Auto-discovered target story from `sprint-status.yaml` as the first backlog item after Story 1.1.
- Reviewed the completed Story 1.1 artifact and recent git history to preserve implementation continuity.
- Implemented `bootstrap` and `readiness` CLI subcommands with orchestration in `src/auto_bean/application/setup.py` and supporting probes/models under `src/auto_bean/domain/` and `src/auto_bean/infrastructure/`.
- Verified the command surface with `uv run --no-sync auto-bean --help`, `uv run --no-sync auto-bean readiness --json`, and `uv run --no-sync auto-bean bootstrap --json`.
- Verified automated coverage with `uv run --no-sync pytest tests/test_package_foundation.py`.

### Completion Notes List

- Comprehensive story context created for Story 1.2.
- Added a thin subcommand CLI for `bootstrap` and `readiness` with machine-friendly JSON output and layered setup orchestration.
- Added typed result and diagnostic models plus reusable environment/tooling probes for macOS support, `uv`, Bison, dependency declarations, repo-local executables, and importability.
- Added deterministic tests for unsupported OS, missing `uv`, missing/unsupported Bison prerequisites, successful bootstrap verification, readiness success, and JSON CLI failure output.
- Updated `README.md`, `pyproject.toml`, and `uv.lock` for the Story 1.2 dependency and maintainer workflow changes.
- Real-environment smoke checks now fail with explicit remediation because the local machine currently exposes `/usr/bin/bison 2.3`; installing Bison >= 3.8 and putting it first on `PATH` is the remaining operator step before a full bootstrap succeeds on this machine.

### File List

- _bmad-output/implementation-artifacts/1-2-bootstrap-local-dependencies-and-readiness-checks-on-macos.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- README.md
- pyproject.toml
- src/auto_bean/__main__.py
- src/auto_bean/application/setup.py
- src/auto_bean/cli/main.py
- src/auto_bean/domain/setup.py
- src/auto_bean/infrastructure/setup.py
- tests/test_package_foundation.py
- uv.lock

### Change Log

- 2026-03-31: Created the implementation-ready Story 1.2 context and marked the story ready for development.
- 2026-03-31: Implemented bootstrap/readiness workflows, supporting diagnostics/models, deterministic tests, and maintainer documentation; advanced story status to `review`.
