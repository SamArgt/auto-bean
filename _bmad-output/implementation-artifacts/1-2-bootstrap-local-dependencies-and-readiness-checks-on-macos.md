# Story 1.2: Bootstrap the auto-bean uv tool on macOS

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a new user on a supported macOS machine,
I want one installation entry point that installs the `auto-bean` uv tool,
so that I can get the product onto my machine before creating a workspace.

## Acceptance Criteria

1. Given a supported macOS environment, when the user runs `uv tool install --from . --force auto-bean`, then it installs or updates the `auto-bean` uv tool from the product source and reports any missing prerequisites with clear remediation guidance.
2. Given installation has completed, when the user verifies the installation, then the system confirms that `uv` is available and that `auto-bean` is discoverable as an installed tool, with clear remediation if the shell still cannot find it.
3. Given a user wants to create a working ledger repository, when they inspect Story 1.2 outputs, then it is clear that workspace creation belongs to a later `auto-bean init <PROJECT-NAME>` command rather than this bootstrap story.

## Tasks / Subtasks

- [x] Reframe the Story 1.2 command surface around direct tool installation instead of a dedicated bootstrap command. (AC: 1, 2, 3)
  - [x] Keep installation as the direct `uv tool install --from <source>` command that can be run from the product repo without assuming `auto-bean` is already installed.
  - [x] Keep user-facing CLI rendering focused on verification and future workspace commands in `src/auto_bean/cli/`.
- [x] Implement install-first verification for supported macOS machines. (AC: 1, 2)
  - [x] Detect unsupported environments and fail closed with explicit remediation.
  - [x] Detect a missing `uv` prerequisite and point the user to the install command.
  - [x] Verify the installed `auto-bean` tool is available after `uv tool install --from . --force auto-bean`.
- [x] Implement a lightweight installation verification path. (AC: 2)
  - [x] Confirm `uv` remains available.
  - [x] Confirm the installed `auto-bean` tool is discoverable on `PATH`, or report the shell remediation required to expose it.
- [x] Reserve workspace initialization for a later story instead of performing it here. (AC: 3)
  - [x] Document that `auto-bean init <PROJECT-NAME>` is the future workspace-creation surface.
  - [x] Keep Story 1.2 free of ledger repo scaffolding, `.auto-bean/` runtime state creation, and first-use workspace files.
- [x] Update automated coverage and maintainer docs for the install-first direction. (AC: 1, 2, 3)
  - [x] Cover unsupported OS detection, missing `uv`, installation verification, and the reserved `init` surface.
  - [x] Update README and `_bmad-output` artifacts so they describe direct installation rather than a dedicated bootstrap command.

## Dev Notes

- Story 1.1 established the packaged `uv` application skeleton. Story 1.2 now uses that package as the source for a uv-managed tool install.
- The installation entry point must not assume that `auto-bean` is already installed, so the contract is the direct `uv tool install --from <source>` command from the product repo.
- This story ends when the user can install the tool and verify that the shell can discover it. It does not create a workspace, a ledger, or governed runtime directories.
- `auto-bean init <PROJECT-NAME>` is now the intended future workspace-creation command surface and belongs to a later story.

### Project Structure Notes

- Keep command parsing and user-facing output in `src/auto_bean/cli/`.
- Keep installation verification orchestration under `src/auto_bean/application/`.
- Keep environment inspection, command execution, and tool discovery under `src/auto_bean/infrastructure/`.

### Developer Guardrails

- Fail closed on unsupported environments. V1 remains macOS-only.
- Do not create a workspace, ledger, or `.auto-bean/` runtime tree in Story 1.2.
- Keep installation idempotent. Re-running `uv tool install --from` should reconcile the installed tool rather than duplicating state.
- Prefer `uv tool install --from <source>` over ad hoc global Python mutation.
- If the tool installs but is not yet on `PATH`, return actionable shell remediation instead of silently succeeding with an unusable command.

### Testing Requirements

- Keep the existing packaged-foundation assertions green.
- Add deterministic tests for:
  - supported vs unsupported OS detection
  - missing `uv` prerequisite reporting
  - verification success when `auto-bean` is on `PATH`
  - placeholder `init` behavior that makes the future scope explicit

### Previous Story Intelligence

- Story 1.1 intentionally stopped at the packaged application foundation.
- The new Story 1.2 direction narrows the next step to installation of the reusable tool, leaving workspace creation for Story 1.4.

### References

- [Epic breakdown](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/epics.md)
- [Architecture](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/architecture.md)
- [PRD](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/prd.md)
- [Previous story](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/1-1-initialize-the-packaged-auto-bean-project-foundation.md)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Re-iterated Story 1.2 on 2026-03-31 to pivot from repo-local readiness bootstrapping to uv tool installation.
- Removed the redundant `bootstrap` CLI command and kept installation as the direct `uv tool install --from` path.
- Kept workspace creation explicitly deferred to a future `auto-bean init <PROJECT-NAME>` workflow.

### Completion Notes List

- Story 1.2 now centers on installing the `auto-bean` uv tool instead of preparing a repo-local `.venv`.
- Removed the dedicated `bootstrap` CLI command and kept install verification focused on `uv` availability and `auto-bean` shell discovery.
- Reserved `init <PROJECT-NAME>` as the future workspace-creation command instead of implementing workspace scaffolding here.
- Updated tests, maintainer docs, and Epic 1 artifacts to match the revised requirement.

### File List

- _bmad-output/implementation-artifacts/1-2-bootstrap-local-dependencies-and-readiness-checks-on-macos.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- _bmad-output/planning-artifacts/epics.md
- README.md
- pyproject.toml
- src/auto_bean/application/setup.py
- src/auto_bean/cli/main.py
- src/auto_bean/domain/setup.py
- src/auto_bean/infrastructure/setup.py
- tests/test_package_foundation.py

### Change Log

- 2026-03-31: Re-iterated Story 1.2 so bootstrap installs the `auto-bean` uv tool and defers workspace creation to a later `init <PROJECT-NAME>` command.
