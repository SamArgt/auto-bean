# Story 1.3: Establish the CI, workflow verification, and diagnostics baseline

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a trust-conscious maintainer-user,
I want the repo to prove basic workflow integrity before ledger-changing automation expands,
so that quality gates are visible and repeatable instead of being implied.

## Acceptance Criteria

1. Given the packaged foundation and install workflow exist, when the baseline quality workflow is configured, then GitHub Actions runs linting, type validation, automated tests, and deterministic workflow smoke checks for core commands, and failures block the baseline from being treated as implementation-ready.
2. Given a readiness-significant or ledger-changing workflow is executed, when the run completes or fails, then the system emits structured local diagnostics and stores inspectable run artifacts under the governed artifacts area, and the artifacts make it possible to review validation, blocked mutations, and troubleshooting context without relying on raw stack traces.

## Tasks / Subtasks

- [x] Add the baseline repository validation workflow in `.github/workflows/`. (AC: 1)
  - [x] Run Ruff checks for the Python codebase and fail the workflow on violations.
  - [x] Run the test suite with `pytest`.
  - [x] Run explicit type validation for core modules instead of treating type safety as implicit.
  - [x] Add deterministic smoke checks that exercise the current core command surface, including at least one failure or blocked path.
- [x] Introduce a reusable workflow-run diagnostics contract in the Python application. (AC: 2)
  - [x] Add a stable `run_id` plus structured event records for workflow stage transitions.
  - [x] Return or persist structured result/error payloads that distinguish validation failures, blocked unsafe mutations, prerequisite failures, and generic execution errors.
  - [x] Keep CLI rendering thin and driven by the structured application result rather than ad hoc print logic.
- [x] Persist governed local artifacts for readiness-significant runs. (AC: 2)
  - [x] Create the `.auto-bean/artifacts/` path through a dedicated infrastructure boundary rather than scattering writes through CLI code.
  - [x] Write inspectable run artifacts for success and failure paths, including enough metadata to review validation status, blocked actions, and troubleshooting context.
  - [x] Keep generated diagnostics and artifacts separate from domain modules and user-owned ledger sources.
- [x] Extend automated coverage for the new baseline. (AC: 1, 2)
  - [x] Add tests for deterministic smoke paths and structured diagnostic/result payloads.
  - [x] Add tests for artifact emission and failure-mode classification.
  - [x] Keep Story 1.1 and 1.2 behavior green while layering in the new observability contract.
- [x] Document the baseline operator expectations for maintainers. (AC: 1, 2)
  - [x] Update README guidance so local verification mirrors CI expectations.
  - [x] Capture the artifact location and troubleshooting intent in repo docs or implementation artifacts, not as hidden tribal knowledge.

## Dev Notes

- Story 1.2 established the current command surface around `auto-bean readiness` and the reserved `auto-bean init <PROJECT-NAME>` flow. Story 1.3 should treat those commands as the first smoke-test targets instead of inventing new temporary commands.
- This story is the architecture-defined second implementation step after packaged project initialization, so it should establish conventions other stories inherit rather than solving only for current setup behavior.
- Delivery integrity is a product requirement, not just engineering polish. CI, deterministic verification, and structured diagnostics are part of the trust model before ledger-changing workflows expand.
- No UX design document exists. Trust-sensitive behavior must therefore stay explicit in CLI output, run artifacts, and acceptance-focused tests.

### Project Structure Notes

- Keep user-facing command parsing and output in `src/auto_bean/cli/`.
- Keep workflow orchestration and run-contract assembly in `src/auto_bean/application/`.
- Keep typed result models, workflow event models, and error classification in `src/auto_bean/domain/`.
- Keep filesystem-backed artifact writing, clock/ID generation, and environment-specific integrations in `src/auto_bean/infrastructure/`.
- Put repository validation under `.github/workflows/`; keep smoke fixtures and tests under `tests/`, ideally in dedicated `smoke/` or clearly named test modules.
- Generated diagnostics must live under `.auto-bean/artifacts/` and must not be mixed into source modules, docs, or user-owned ledger files.

### Developer Guardrails

- Reuse the existing `WorkflowResult`/diagnostic pattern from Story 1.2 instead of introducing a second result envelope for similar setup flows.
- Evolve the current setup service toward the architecture contract: stable `run_id`, structured event records, explicit error codes, and inspectable artifacts for readiness-significant runs.
- Keep CLI code free of business logic. Parsing, selecting JSON vs human output, and rendering are fine; filesystem mutation, event generation, and artifact persistence belong below the CLI layer.
- Fail closed when verification fails. CI should block merges when lint, tests, type validation, or smoke checks regress.
- Smoke checks must remain deterministic. Cover the standard happy path plus at least one blocked/failure path, and avoid dependence on ambient machine state that would make CI flaky.
- Artifact persistence must go through a governed path. Do not write ad hoc logs or JSON blobs into random repo locations.
- Preserve the separation between stable user-owned assets and evolving tool logic; Story 1.3 should add baseline runtime artifacts, not workspace ledger scaffolding.

### Testing Requirements

- Keep the existing package foundation and setup tests passing.
- Add CI-covered tests for:
  - structured workflow results and event emission
  - run artifact creation for readiness-significant execution
  - deterministic smoke execution of `auto-bean readiness`
  - at least one blocked/failure smoke scenario such as unsupported environment or missing tool discovery
  - type-validation command wiring so CI fails if the configured checker reports issues
- Keep local verification fast enough to support the architecture goal that readiness checks on a bootstrapped workspace finish within 2 minutes.

### Previous Story Intelligence

- Story 1.2 already established explicit error codes such as `unsupported_environment`, `missing_uv`, `missing_auto_bean_on_path`, and `init_not_implemented`. Reuse and extend that style rather than replacing it with unstructured failure text.
- The current code already separates `cli`, `application`, `domain`, and `infrastructure` layers. Story 1.3 should deepen those boundaries for diagnostics and artifacts rather than collapsing concerns into one module.
- Recent Story 1.2 work touched `pyproject.toml`, `src/auto_bean/application/setup.py`, `src/auto_bean/cli/main.py`, `src/auto_bean/domain/setup.py`, `src/auto_bean/infrastructure/setup.py`, `tests/test_package_foundation.py`, and `README.md`; Story 1.3 will likely extend the same surfaces plus add `.github/workflows/`.

### Git Intelligence

- Recent commits show a pattern of updating the story artifact, `sprint-status.yaml`, maintainer docs, setup modules, and tests together (`03ba6e0`, `99f9f99`). Keep Story 1.3 aligned with that pattern so the repo, docs, and generated artifacts move in sync.
- There is no existing `.github/workflows/` baseline yet, which means this story should establish the first repository-level quality workflow rather than refactor an existing CI setup.

### Latest Technical Information

- `uv` remains the project/runtime manager and supports packaged application workflows and tool installation; keep Story 1.3 aligned with that `uv`-managed workflow instead of introducing a second package manager. Source: [uv docs](https://docs.astral.sh/uv/)
- GitHub Actions is still the required CI surface in the architecture, so the baseline should be implemented as repository workflows rather than an alternate hosted CI system. Source: [GitHub Actions docs](https://docs.github.com/actions)
- Ruff remains the intended fast lint/format gate for Python projects, which makes it a good fit for the baseline repository validation step. Source: [Ruff docs](https://docs.astral.sh/ruff/)
- `pytest` remains the expected automated test runner in the architecture and current repo configuration. Source: [pytest docs](https://docs.pytest.org/)

### References

- [Epic breakdown](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/epics.md)
- [Architecture](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/architecture.md)
- [PRD](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/prd.md)
- [Previous story](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/1-2-bootstrap-local-dependencies-and-readiness-checks-on-macos.md)
- [Sprint status](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/sprint-status.yaml)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story 1.3 created on 2026-03-31 from the next backlog item in `sprint-status.yaml`.
- Context synthesized from Epic 1, the PRD, the architecture document, Story 1.2, and recent git history.
- Development started on 2026-03-31 10:23:32 CEST after loading the story, architecture, repo configuration, and current setup workflow code.
- Added a repository baseline workflow, `uv`-managed lint/type/test commands, and deterministic smoke coverage for the `readiness` and blocked `init` CLI paths.
- Implemented structured workflow diagnostics with stable `run_id`, ordered events, explicit error categories, and governed JSON artifact persistence.
- Verified the full regression baseline with `uv run ruff check src tests scripts`, `uv run mypy src tests scripts`, `uv run pytest`, `uv run python scripts/run_smoke_checks.py`, and `uv lock`.

### Implementation Plan

- Add failing tests first for the new structured diagnostics contract, governed artifact persistence, and deterministic smoke coverage.
- Extend the setup workflow result model with stable run metadata, stage events, error classification, and artifact references.
- Introduce infrastructure-backed artifact persistence under `.auto-bean/artifacts/` and keep CLI rendering driven by structured results.
- Add repository CI for Ruff, pytest, type validation, and smoke checks, then update maintainer-facing docs to match local verification.

### Completion Notes List

- Added `.github/workflows/repository-baseline.yml` so GitHub Actions now blocks on Ruff, mypy, pytest, and deterministic CLI smoke checks.
- Extended the setup workflow contract with `run_id`, workflow stage events, explicit error categories, started timestamps, and artifact references for both JSON and human-readable CLI output.
- Persisted inspectable governed run artifacts under `.auto-bean/artifacts/` through the infrastructure layer instead of CLI-side file writes.
- Added deterministic smoke and artifact tests while keeping the Story 1.1 and 1.2 behavior green.
- Updated maintainer docs with local CI-equivalent verification commands and the troubleshooting intent for governed artifacts.

### File List

- .github/workflows/repository-baseline.yml
- .gitignore
- README.md
- _bmad-output/implementation-artifacts/1-3-establish-the-ci-workflow-verification-and-diagnostics-baseline.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- docs/diagnostics.md
- pyproject.toml
- scripts/run_smoke_checks.py
- src/auto_bean/application/setup.py
- src/auto_bean/application/smoke.py
- src/auto_bean/cli/main.py
- src/auto_bean/domain/setup.py
- src/auto_bean/infrastructure/setup.py
- tests/test_package_foundation.py
- tests/test_setup_diagnostics.py
- tests/test_smoke_checks.py
- uv.lock

### Change Log

- 2026-03-31: Added the repository CI baseline, structured workflow diagnostics, governed artifact persistence, deterministic smoke checks, and maintainer troubleshooting documentation for Story 1.3.

### Review Findings

- [x] [Review][Patch] Artifact persistence breaks installed-tool readiness outside the repo checkout [src/auto_bean/application/setup.py:283]
- [x] [Review][Patch] Runtime exceptions bypass the structured `execution_error` contract [src/auto_bean/cli/main.py:49]
