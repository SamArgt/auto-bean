# Story 1.6: Deliver the Codex-first quickstart for first meaningful use

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a new user,
I want a quickstart workflow that shows how to bootstrap, initialize a ledger, and reach first value,
so that I can become operational in the first session without needing a public SDK or external API.

## Acceptance Criteria

1. Given a new user opening the repo for the first time, when they follow the quickstart guidance, then they can install the tool, initialize the workspace, create the base ledger, and understand the next import-oriented workflow, and the guidance uses Codex skill-driven interaction as the primary interface.
2. Given the quickstart documentation is available, when a user follows it end to end, then the documented path does not depend on a public SDK or formal external API, and it positions the product as an evolving local tool within the repository.

## Tasks / Subtasks

- [x] Author the primary first-session quickstart in `README.md`. (AC: 1, 2)
  - [x] Expand `README.md` into the single onboarding source for now, covering only the currently supported path: `uv tool install --from . --force auto-bean`, `auto-bean readiness`, `auto-bean init <PROJECT-NAME>`, workspace validation, and Fava inspection.
  - [x] Make Codex the primary interaction model in the guidance by explicitly telling the user when to work through installed workspace skills rather than looking for a public SDK or external API.
  - [x] Define “first meaningful use” honestly for current V1 scope: the user reaches a bootstrapped workspace, validates `ledger.beancount`, can inspect it in Fava, and knows where later statement-import work will enter the workflow.
- [x] Keep adjacent entrypoints aligned with the README quickstart instead of forcing users to reconcile multiple sources. (AC: 1, 2)
  - [x] Consolidate workspace-facing guidance into `workspace_template/AGENTS.md` so it remains consistent with the README quickstart’s skill-first framing and post-init next steps without introducing a second onboarding document.
  - [x] If the current CLI help or init result output creates ambiguity about the quickstart path, add only the smallest clarifying changes needed in `src/auto_bean/cli/main.py` or the setup-service-rendered next steps; do not turn this story into a new CLI command.
  - [x] Keep any future split into dedicated docs deferred until the README becomes meaningfully too large or the onboarding flow gains enough complexity to justify it.
- [x] Represent the next import-oriented workflow without inventing unsupported product behavior. (AC: 1, 2)
  - [x] Explain that statement-import workflows are the next major operating path, but are delivered in later stories rather than through a public SDK today.
  - [x] Point users at the existing workspace runtime boundaries that matter now, especially `ledger.beancount`, `beancount/`, `statements/raw/`, `.auto-bean/`, and `.agents/skills/auto-bean-apply/`.
  - [x] Avoid documenting commands, APIs, or skills that do not yet exist in the repo.

## Dev Notes

- Epic 1 now has the setup foundation, readiness checks, workspace initialization, and structural-review skill path in place. Story 1.6 should convert those implemented surfaces into a trustworthy first-session onboarding flow without introducing unnecessary documentation sprawl.
- The PRD and architecture both state that Codex skills are the primary interaction layer and that the essential documentation requirement for V1 is a strong quickstart. This story should therefore be documentation-led, with code changes only where they materially reduce onboarding ambiguity.
- The architecture’s recommended repo shape mentions a dedicated quickstart doc, but the current product decision is to keep onboarding centralized in `README.md` until that becomes unwieldy. The story should honor that narrower documentation footprint.
- No UX design artifact exists. Trust-sensitive onboarding expectations must therefore be made explicit in documentation language: what is supported today, what requires the coding agent, what is not yet implemented, and where risky structural edits go through review.
- Story 1.5 established that authored skill behavior lives in `skill_sources/` and that `auto-bean init` materializes runtime skills into the generated workspace. The quickstart must reflect that boundary and point users at the installed runtime skill under `.agents/skills/auto-bean-apply/`, not at product-repo runtime copies.
- Current supported product surfaces are `auto-bean readiness` and `auto-bean init <PROJECT-NAME>`, plus the generated workspace helper scripts. Story 1.6 must not imply there is already a shipped import command, SDK, or external API.

### Project Structure Notes

- Put the detailed first-session walkthrough directly in `README.md`.
- Keep `README.md` as both the product-repo landing page and the single quickstart source for now.
- Keep workspace-specific operating guidance in `workspace_template/AGENTS.md` while `README.md` remains the single onboarding source.
- Keep CLI parsing thin in `src/auto_bean/cli/main.py`; if any code changes are needed, prefer small wording or next-step adjustments over new command surfaces.

### Developer Guardrails

- Do not invent a public SDK, import API, or unsupported workflow just to make the quickstart feel more complete.
- Do not document future commands as if they are implemented. Be explicit about what is available now versus what later stories introduce.
- Keep the quickstart Codex-first: the user should understand that agent/skill-driven workflows are the stable surface, while Python helpers and CLI commands support setup and validation.
- Preserve the two-repository model. The quickstart should distinguish between the product repo where `auto-bean` is authored and the generated user workspace where the ledger, statements, memory, artifacts, and installed skills live.
- Keep product-repo and workspace paths accurate. The quickstart must not tell users to edit product-repo `.agents/skills/` or to treat the product repo as the live ledger workspace.
- Treat documentation accuracy as a trust boundary. If a command is optional, unsupported, or deferred, say so directly rather than smoothing it over with vague prose.

### Technical Requirements

- Align the quickstart with the current setup implementation and README-supported commands: install via `uv tool install`, verify with `auto-bean readiness` or `uv tool run --from . auto-bean readiness`, create the workspace with `auto-bean init`, then operate inside the generated workspace.
- Keep the quickstart consolidated in `README.md`; do not introduce a second onboarding document unless the scope grows enough to justify one later.
- Explicitly cover the current init behavior that matters to onboarding: Codex is the only supported coding-agent choice, the generated workspace is a separate Git repository, a workspace-local `.venv` is created, and the scaffold is validated before success is reported.
- Include the supported post-init validation and inspection surfaces already created by Story 1.4: `./scripts/validate-ledger.sh`, `./scripts/open-fava.sh`, `./.venv/bin/bean-check ledger.beancount`, and `./.venv/bin/fava ledger.beancount`.
- Make the “next import-oriented workflow” concrete without overpromising implementation: statements belong under `statements/raw/`, and later stories will introduce normalized import/review workflows from there.
- If clarifying code output is needed, keep it limited to help text or next-step messaging that reinforces the documented path.

### Architecture Compliance

- Follow the architecture’s documentation and product-evolution direction: onboarding is quickstart-driven, local-first, Codex-first, and not based on a public SDK.
- Apply that direction using the current repo’s simpler documentation strategy: one README-led quickstart rather than multiple onboarding documents.
- Keep user-facing workflow explanation in docs and authored guidance, with Python code limited to support behavior already present in setup/readiness flows.
- Maintain the boundary that authored skill source lives in `skill_sources/` in the product repo, while installed runtime skill content lives under `.agents/skills/` in the user workspace.
- Keep the quickstart consistent with the two-repository model and the trust model established by Stories 1.4 and 1.5.
- Do not introduce speculative architecture such as a new onboarding command, remote service dependency, or API client surface.

### Library / Framework Requirements

- Continue using the current packaged Python application and `uv`-managed installation flow already established in the repo.
- Keep Beancount validation centered on `ledger.beancount` as the stable entrypoint.
- Keep Fava guidance centered on opening the generated workspace’s ledger through the workspace-local runtime.
- Use only current, supported commands already backed by the repo implementation and docs.

### File Structure Requirements

- Primary expected files to create or modify for this story:
  - `README.md`
  - `workspace_template/AGENTS.md`
- Possible lightweight code-touch surfaces only if needed for clarity:
  - `src/auto_bean/cli/main.py`
  - `src/auto_bean/application/setup.py`
- Do not add live installed runtime skills under product-repo `.agents/skills/`.
- Do not create placeholder import guides, SDK docs, or API references that the implementation does not support yet.

### Previous Story Intelligence

- Story 1.4 established the real `auto-bean init <PROJECT-NAME>` workflow, the generated workspace scaffold, workspace helper scripts, and the repo-vs-workspace boundary. Story 1.6 should use those implemented details directly in the quickstart.
- Story 1.5 clarified the trust model around structural changes and moved authored skill behavior into `skill_sources/`, with runtime installation happening during `auto-bean init`. The quickstart should build on that skill-first model and point users at the installed workspace skill instead of suggesting CLI-first structural editing.
- The current repo still has no dedicated quickstart document and only minimal workspace guide content. This story should assemble those pieces into a single, accurate README-led first-session path instead of splitting them prematurely.

### Git Intelligence

- Recent commits (`fb3131c`, `db681c2`, `ba8f532`) bundled story artifacts, sprint tracking, docs, and implementation changes together. Keep that synchronization pattern for Story 1.6 so onboarding guidance and supporting surfaces do not drift apart.
- The repo currently has only `docs/diagnostics.md` under `docs/`, but the chosen direction is to keep the first-session path in `README.md` until a dedicated doc is clearly warranted.

### Latest Technical Information

- The Beancount docs still describe `bean-check /path/to/your/file.beancount` as the standard validation flow, which supports keeping `ledger.beancount` as the quickstart’s validation entrypoint for the generated workspace. Source: [Getting Started with Beancount](https://beancount.github.io/docs/getting_started_with_beancount.html)
- Fava’s documented usage continues to center on opening a ledger file directly, which matches the current workspace guidance to run Fava against `ledger.beancount` rather than inventing an alternate entrypoint. Source: [Fava Documentation](https://beancount.github.io/fava/)
- The current repo implementation already exposes setup through `uv tool install --from . --force auto-bean`, `auto-bean readiness`, and `auto-bean init <PROJECT-NAME>`. Story 1.6 should document those supported surfaces instead of introducing a new onboarding command.

### References

- [Epic breakdown](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/epics.md)
- [Architecture](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/architecture.md)
- [PRD](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/prd.md)
- [Previous story](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/1-5-inspect-and-finalize-structural-ledger-changes-through-the-agent-workflow.md)
- [Story 1.4](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/1-4-create-a-new-base-beancount-ledger-workspace.md)
- [Sprint status](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/sprint-status.yaml)
- [README](/Users/sam/Projects/auto-bean/README.md)
- [CLI entrypoint](/Users/sam/Projects/auto-bean/src/auto_bean/cli/main.py)
- [Setup service](/Users/sam/Projects/auto-bean/src/auto_bean/application/setup.py)
- [Workspace agents guide](/Users/sam/Projects/auto-bean/workspace_template/AGENTS.md)
- [Diagnostics docs](/Users/sam/Projects/auto-bean/docs/diagnostics.md)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story 1.6 created on 2026-04-03 from the first backlog story in `sprint-status.yaml`.
- No `project-context.md` or UX document was present in the repo, so story guidance was synthesized from the PRD, architecture, Epic 1, Stories 1.4 and 1.5, the current README/workspace docs, and the current CLI/setup implementation.
- Story scope was kept documentation-first because the required runtime setup surfaces already exist; code changes are optional and should be minimal unless current help or next-step output materially confuses the first-session path.
- Story guidance explicitly avoids inventing a public SDK, import command, or unsupported onboarding shortcut. The quickstart should be honest about current scope and clear about the next import-oriented phase.
- Development started on 2026-04-03 after confirming Story 1.6 was the first `ready-for-dev` item in `sprint-status.yaml`; sprint status was moved to `in-progress` before implementation edits.

### Implementation Plan

- Add a small regression test around `init` next-step guidance if runtime output needs a quickstart-alignment hint, then keep any setup-service change minimal.
- Rewrite `README.md` into the single first-session quickstart source for installation, readiness, initialization, validation, Fava inspection, and the current statement-import boundary.
- Consolidate the workspace guidance into `workspace_template/AGENTS.md` so it matches the README's Codex-first guidance, runtime boundaries, and post-init next steps.
- Run focused and full validation after the documentation and messaging updates, then update story tracking only if all checks pass.

### Completion Notes List

- Identified `1-6-deliver-the-codex-first-quickstart-for-first-meaningful-use` as the next backlog story from `sprint-status.yaml`.
- Created a comprehensive story file that centers `README.md` as the primary quickstart deliverable, with workspace-guide alignment and a tightly scoped documentation-only implementation target.
- Incorporated Story 1.5’s skill-source/runtime-installation boundary so the quickstart points users at the installed workspace skill under `.agents/skills/auto-bean-apply/`.
- Rewrote `README.md` into the single first-session quickstart source, covering installation, readiness, workspace creation, validation, Fava inspection, the product-repo versus workspace boundary, and the current statement-import runway without inventing unsupported APIs.
- Consolidated the workspace guidance into `workspace_template/AGENTS.md` with the same Codex-first framing, runtime path boundaries, and supported post-init commands.
- Added a minimal `init` next-step hint in `src/auto_bean/application/setup.py` so the generated workspace output now points users to `AGENTS.md` for the intended operating flow.
- Verified the implementation with `uv run pytest`, `uv run ruff check src tests scripts`, `uv run mypy src tests scripts`, and `uv run python scripts/run_smoke_checks.py`.

### File List

- README.md
- _bmad-output/implementation-artifacts/1-6-deliver-the-codex-first-quickstart-for-first-meaningful-use.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- src/auto_bean/application/setup.py
- tests/test_setup_diagnostics.py
- workspace_template/AGENTS.md

### Change Log

- 2026-04-03: Reworked Story 1.6 into a README-led quickstart, aligned the generated workspace guidance, and added a minimal `init` next-step hint plus regression coverage for the Codex-first onboarding path.
