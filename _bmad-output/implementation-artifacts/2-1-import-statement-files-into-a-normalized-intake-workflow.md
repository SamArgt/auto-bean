# Story 2.1: Import statement files into a normalized intake workflow

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user managing real financial records,
I want PDF, CSV, and Excel statements converted through the Docling CLI into a normalized statement intake folder,
so that different statement formats can enter the ledger pipeline consistently without making auto-bean own bespoke document parsing code.

## Acceptance Criteria

1. Given a supported statement file in PDF, CSV, or Excel format under the workspace statement intake area, when the import-intake workflow is run, then Codex uses the locally available Docling CLI to extract normalized parse results, reports parsing failures clearly without mutating the ledger, and writes an inspectable parse output under `statements/parsed/`.
2. Given the workspace does not yet have the Docling CLI or its required runtime dependencies available, when `auto-bean init` prepares the workspace, then it installs or guides installation of Docling into the workspace runtime, explains anything still missing, and does not claim import intake is ready until the CLI is available.
3. Given multiple supported statement files from different sources, when the user imports them into the same ledger workflow, then the import orchestration skill can spawn parallel Codex sub-agents, assign one raw statement or bounded batch per sub-agent, collect the parse results, and write distinguishable parsed files using the same normalized output contract.
4. Given raw statement files already exist in `statements/raw/`, when the user asks the import-intake workflow to find new statements, then the workflow reads and updates `statements/import-status.yml`, detects files that do not yet have a current corresponding parse output under `statements/parsed/`, and parses only those new or stale inputs unless the user asks otherwise.
5. Given the user asks to re-parse a specific statement, when they provide the statement path or filename, then the workflow uses `statements/import-status.yml` to target that statement even if a prior parse output exists, preserves prior outputs or records supersession according to the parsed-output naming contract, updates the statement's parse status, and does not re-parse unrelated statements.

## Tasks / Subtasks

- [x] Define the workspace statement parsing contract. (AC: 1, 3, 4, 5)
  - [x] Add `statements/parsed/` to the generated workspace skeleton as the durable location for normalized parse outputs.
  - [x] Add `statements/import-status.yml` to the generated workspace skeleton as the durable index of raw statement parse state.
  - [x] Define a small JSON contract for parsed statement outputs that includes `parse_run_id`, `source_file`, `source_fingerprint` or equivalent change marker, `source_format`, `parser`, `parse_status`, `parsed_at`, `warnings`, `blocking_issues`, and normalized rows or extracted records.
  - [x] Define the import status YAML contract with one entry per raw statement, including source path, source fingerprint/change marker, current status, latest parse output path, latest parse run id, parser identifier, timestamps, warnings, and blocking issues.
  - [x] Keep paths workspace-relative where practical and keep all JSON keys in `snake_case`.
  - [x] Keep the contract narrow: extracted statement facts and parse diagnostics only, not final Beancount postings, account creation, reconciliation decisions, or memory writes.
- [x] Install and expose Docling CLI readiness in the workspace. (AC: 1, 2)
  - [x] Add Docling CLI installation or materialization to the `auto-bean init` workspace bootstrap workflow.
  - [x] Keep any product-authored orchestration in `skill_sources/` and do not author live runtime copies directly under product-repo `.agents/skills/`.
  - [x] Record in workspace guidance that statement normalization routes through the local Docling CLI for supported PDF, CSV, and Excel inputs.
- [x] Install required local dependencies for Docling CLI. (AC: 2)
  - [x] Ensure `auto-bean init` installs the `docling` package into the workspace-local runtime and exposes the `docling` CLI before import intake is considered ready.
  - [x] Prefer the workspace-local Python environment and `uv` for dependency installation and readiness checks.
  - [x] If additional system dependencies are needed for the chosen Docling conversion path, surface a clear remediation message and do not claim the related parsing path is ready.
- [x] Implement the import-intake workflow mostly in authored skill guidance, not new Python parsing code. (AC: 1, 2, 3, 4, 5)
  - [x] Create or update `skill_sources/auto-bean-import/` as the auto-bean orchestration skill for statement intake.
  - [x] Have the auto-bean import skill call the local Docling CLI for format-specific conversion rather than implementing custom PDF/CSV/XLSX parsing in `src/auto_bean/`.
  - [x] Teach the import skill to accept at least two modes: discover new raw statements in `statements/raw/`, or re-parse a specific user-provided statement path.
  - [x] Teach the import skill to read `statements/import-status.yml` before choosing work, then compare raw statements against both the status index and existing `statements/parsed/` outputs so it can identify new or stale files without reprocessing everything by default.
  - [x] Teach the import skill to update `statements/import-status.yml` after each parse attempt, including successful, warning, blocked, failed, stale, and superseded states.
  - [x] Use Python support code only for small install/materialization or validation helpers when markdown workflow guidance is not enough.
  - [x] Do not add broad import adapter modules unless there is a concrete non-parsing orchestration reason.
- [x] Support parallel parsing through Codex sub-agents. (AC: 3)
  - [x] In the import skill workflow, explicitly allow Codex to spawn worker sub-agents for multi-file parsing when the user asks to import a set of files, parse all new files, or otherwise requests parallel processing.
  - [x] Assign each sub-agent a bounded input: one raw statement file by default, or a small batch only when file count exceeds the configured concurrency cap.
  - [x] Require each sub-agent to use the correct Docling CLI invocation for the assigned source format and return a structured parse result containing the normalized output path, parse status, warnings, and blocking issues.
  - [x] Have the parent import orchestration skill consolidate sub-agent results into a single user-facing summary and fail closed for any statement whose parse worker fails, times out, or needs approval that cannot be surfaced.
  - [x] Respect Codex sub-agent sandbox and approval behavior; do not design the workflow to bypass approvals or mutate files outside the worker's assigned parse-output target.
- [x] Persist parse results under `statements/parsed/`. (AC: 1, 3, 4, 5)
  - [x] Write one parse output per source file or per run using stable, descriptive filenames that preserve source identity.
  - [x] Include `parse_run_id` and source fingerprint/change marker in each output so the discover mode can tell whether a raw statement is already parsed or stale.
  - [x] Keep `statements/import-status.yml` synchronized with each parse output so the agent can quickly identify which raw statements need parsing and what their current state is.
  - [x] For re-parse, either create a new versioned parse output or mark the new output as superseding the prior one; do not silently overwrite prior parse context unless the user explicitly asks for overwrite behavior.
  - [x] Include enough extracted rows/records for downstream review and reconciliation: source row/page reference, date if available, description/payee text if available, amount if available, currency if available, raw extracted fields/text, and parser warnings or confidence notes if available.
  - [x] Treat scanned or textless PDFs as blocked parse results with structured issues unless the configured Docling CLI conversion path and available dependencies can extract usable text.
  - [x] Do not write parse results to `.auto-bean/artifacts/` for this story.
- [x] Preserve ledger and memory boundaries. (AC: 1, 3)
  - [x] Do not mutate `ledger.beancount` or `beancount/**`.
  - [x] Do not write durable memory under `.auto-bean/memory/**`.
  - [x] Do not create first-seen account proposals, reconciliation candidates, duplicate/transfer decisions, or mutation plans in this story.
  - [x] Keep `statements/raw/` as the raw input location and `statements/parsed/` as the normalized parse-output location.
  - [x] Keep `statements/import-status.yml` as the parse-state index; do not move parse state into `.auto-bean/memory/`.
- [x] Add lightweight validation and documentation. (AC: 1, 2, 3, 4, 5)
  - [x] Add tests or smoke checks that verify workspace init/materialization installs or validates Docling CLI readiness, includes the import skill, and creates `statements/parsed/` plus `statements/import-status.yml`.
  - [x] Add fixture-free or synthetic-file checks for the normalized parse-output schema if practical.
  - [x] Update `README.md` and `workspace_template/AGENTS.md` to describe the new `statements/parsed/` boundary and the dependency on locally available Docling CLI support.
  - [x] Keep docs explicit that Story 2.1 parses statements into normalized files only; later stories handle account proposals, review, reconciliation, mutation, and memory.

## Dev Notes

- This rewrite changes the core implementation strategy: auto-bean should not build and own a bespoke document parsing subsystem in Python for Story 2.1. Codex should use the locally available Docling CLI to perform format-specific extraction for supported statement formats.
- Treat `skill_sources/auto-bean-import/` as the orchestration layer that decides when and how to invoke Docling CLI, where outputs go, and what trust boundaries apply.
- The import orchestration skill must be able to run in two entry modes: discover unparsed or stale raw files under `statements/raw/`, and re-parse a specific statement named by the user. In both modes, it should use `statements/import-status.yml` as the first parse-state index before falling back to filesystem discovery.
- For multi-statement work, the import orchestration skill should use Codex sub-agents as a parallel fan-out mechanism: the parent skill discovers or receives the file list, spawns bounded workers, delegates one statement or small batch per worker, and consolidates the parse outputs and errors.
- Treat `statements/parsed/` as the durable statement-derived output location. This is separate from `.auto-bean/artifacts/`; do not persist parse results under `.auto-bean/artifacts/` in this story.
- No UX document or `project-context.md` exists in this repo. Trust-sensitive expectations must therefore be explicit in workflow guidance: parse failures are visible, source files are preserved, parsed outputs are inspectable, and no ledger mutation happens during parsing.
- The product repo is not the live ledger workspace. Runtime raw statements and parsed statement outputs belong in generated user workspaces under `statements/raw/` and `statements/parsed/`.

### Project Structure Notes

- Expected product-repo surfaces:
  - `skill_sources/auto-bean-import/` for authored auto-bean import orchestration behavior.
  - `workspace_template/statements/parsed/.gitkeep` so generated workspaces have a durable parse-output folder.
  - `workspace_template/statements/import-status.yml` so generated workspaces have a durable parse-state index.
  - `workspace_template/AGENTS.md` for runtime guidance about `statements/raw/`, `statements/parsed/`, and local Docling CLI readiness.
  - `src/auto_bean/init.py` for workspace-init installation, materialization, or readiness checks for Docling CLI.
  - `src/auto_bean/cli.py` only if a thin internal helper is needed for installation or readiness checks.
  - `tests/` for workspace materialization and contract checks.
  - `pyproject.toml` and `uv.lock` only if product-level dependency changes are truly required.
- Expected runtime workspace surfaces:
  - `statements/raw/` contains raw source statements and should not be rewritten.
  - `statements/parsed/` contains normalized parse outputs produced from raw statement files.
  - `statements/import-status.yml` contains the current parse-state index for raw statements.
  - `.agents/skills/auto-bean-import/` contains auto-bean's installed import orchestration skill.
  - The workspace-local runtime exposes the `docling` CLI used by the import orchestration skill.
- Avoid adding live installed runtime skills under product-repo `.agents/skills/`.
- Avoid adding new Python parsing modules unless the dependency/materialization layer genuinely needs a small helper.

### Developer Guardrails

- Do not implement custom PDF, CSV, or Excel parsing logic in auto-bean unless Docling CLI is unavailable and the story is explicitly re-scoped.
- Do not mutate ledger files in this story. A successful intake run means parsed statement output exists under `statements/parsed/`, not that any ledger change was accepted.
- Do not write durable memory in this story. Source-specific memory belongs to Story 2.4 and later memory workflows.
- Do not implement account creation in this story. First-seen account proposals belong to Story 2.2.
- Do not implement review/approval UI or mutation application in this story. Review belongs to Story 2.3 and later apply/reconciliation workflows.
- Do not invent a public SDK. The user-facing surface remains Codex skills in the workspace.
- Do not store parse outputs in `.auto-bean/artifacts/` for this story.
- Do not infer parse state only from conversation history. Use `statements/import-status.yml` plus filesystem checks so later agent runs can resume accurately.
- Do not let sub-agents choose their own scope. Each parse worker should receive an explicit raw statement path, expected Docling conversion mode, output contract, and target `statements/parsed/` path or naming rule.
- Do not treat a successful parallel batch as fully successful if one sub-agent fails. Summarize per-file status and leave failed inputs clearly blocked or unparsed.

### Technical Requirements

- Install Docling CLI during `auto-bean init` so statement conversion is available in the workspace runtime before the first import run.
- Delegate supported PDF, CSV, and Excel statement conversion to the `docling` CLI.
- Prefer the workspace-local Python environment and `uv` for Python dependency installation and CLI readiness checks.
- Use the local Docling CLI in a deterministic way, for example by writing Docling JSON output to a temporary or staging location and translating that output into the story's normalized parse contract.
- Generate parse outputs under `statements/parsed/` as structured JSON with stable names and inspectable issue details.
- Maintain `statements/import-status.yml` as the durable parse-state index for `statements/raw/` inputs and `statements/parsed/` outputs.
- Use stable status values such as `new`, `parsing`, `parsed`, `parsed_with_warnings`, `blocked`, `failed`, `stale`, and `superseded`, or an equally explicit finite set.
- Use deterministic filenames and run identifiers so repeated runs over the same statement can be compared.
- Support discovery mode by reading `statements/import-status.yml`, scanning `statements/raw/` for supported file extensions, and comparing against `statements/parsed/` outputs by source path plus fingerprint/change marker.
- Support targeted re-parse mode by accepting a specific user-provided path or filename and processing it even when an earlier parse output exists.
- For parallel parsing, follow Codex's sub-agent model: spawn specialized workers only when the workflow/user request calls for it, keep each worker bounded to its assigned statement, and consolidate results in the parent workflow.
- Keep all primary financial data local; no external service should be required for this story.

### Architecture Compliance

- The architecture calls for multi-format statement import feeding a normalized model before ledger posting decisions. This story satisfies that by producing normalized parsed files, not by creating postings or mutation plans.
- The architecture also says Codex skills are the primary user interface and Python support code should support skill execution. This rewrite follows that: Docling CLI performs document conversion, auto-bean import guidance orchestrates, and Python code changes stay minimal.
- Codex sub-agents are appropriate here because multi-statement parsing is highly parallel. The import orchestration skill should use them to divide independent raw statement parsing work while the parent workflow owns discovery, dependency readiness, output naming, and final result consolidation.
- Runtime data boundaries for this story are:
  - `statements/raw/` for raw statement files.
  - `statements/parsed/` for normalized parse outputs.
  - `statements/import-status.yml` for the parse-state index.
  - `.agents/skills/` for installed runtime skills.
  - `ledger.beancount` and `beancount/**` remain untouched.
  - `.auto-bean/memory/**` remains untouched.
- Where older architecture text suggests import artifacts under `.auto-bean/artifacts/`, this story intentionally overrides that for parse outputs based on the new product decision to persist parse results under `statements/parsed/`.

### Library / Tool Requirements

- Docling supports local CLI conversion of supported document formats and defaults to Markdown output, with explicit `--to json` support for structured output. Source: https://github.com/docling-project/docling/blob/main/README.md
- Docling CLI supports batch conversion, custom output directories, and multi-format conversion such as `docling ./input/dir --from pdf --from docx --to md --to json --output ./scratch`. Source: https://github.com/docling-project/docling/blob/main/docs/v2.md
- Docling documents support for PDF, XLSX, HTML, and CSV input formats in its supported formats guidance. Source: https://github.com/docling-project/docling/blob/main/docs/usage/supported_formats.md
- Docling installation guidance documents `pip install docling` and requires Python 3.10 or higher. Source: https://github.com/docling-project/docling/blob/main/README.md
- Codex developer docs describe subagents as a way to spawn specialized agents in parallel and collect their results in one response; they also note that Codex only spawns subagents when explicitly asked and that subagents inherit the current sandbox policy. Source: https://developers.openai.com/codex/subagents
- Do not expose internal tool implementation details in user-facing workspace guidance; describe the supported files, required local Docling readiness, and expected outputs instead.

### File Structure Requirements

- Likely files to create or modify when implementing this story:
  - `skill_sources/auto-bean-import/SKILL.md`
  - `skill_sources/auto-bean-import/agents/openai.yaml` if runtime skill metadata is needed.
  - `workspace_template/statements/parsed/.gitkeep`
  - `workspace_template/statements/import-status.yml`
  - `workspace_template/AGENTS.md`
  - `README.md`
  - `src/auto_bean/init.py` for Docling installation/materialization and dependency checks.
  - `tests/test_setup_diagnostics.py` or a focused workspace materialization test.
  - `pyproject.toml` and `uv.lock` only if product-level dependencies are needed; prefer installing Docling in the workspace runtime when feasible.
- Do not add `src/auto_bean/imports.py` just to parse files; parsing belongs to the local Docling CLI path for this story.
- Do not add generated user-workspace runtime files directly to product-repo `.agents/skills/`.
- Do not store parse fixtures or generated parse outputs under `.auto-bean/`.
- Do not store import parse status under `.auto-bean/`; use `statements/import-status.yml`.

### Testing Requirements

- Run `uv run ruff check` and `uv run ruff format` after code changes.
- Run `uv run mypy` when changing Python code.
- Run `uv run pytest` when changing Python code.
- Add tests that verify generated workspaces include `statements/parsed/`.
- Add tests that verify generated workspaces include `statements/import-status.yml`.
- Add tests or smoke checks that verify workspace guidance and runtime readiness include `auto-bean-import` plus Docling CLI availability, if materialized locally.
- Add workflow-level tests or fixture checks for raw-statement discovery using `statements/import-status.yml`: new file detected, already parsed file skipped, stale file detected after source change, and explicit re-parse processes only the requested input.
- Add a lightweight authored-skill validation check that the import workflow includes bounded sub-agent delegation instructions and parent-level result consolidation.
- Add a lightweight schema validation test for example parsed-output JSON if the contract is encoded in repo files.
- Keep existing smoke checks passing.

### Previous Story Intelligence

- Story 1.6 established that `README.md` is the current first-session quickstart and that `workspace_template/AGENTS.md` owns generated-workspace operating guidance. Story 2.1 should update those only enough to describe import intake truthfully.
- Story 1.6 explicitly left statement import as the next major operating path and warned not to document unsupported commands. This story may now introduce the first supported import-intake workflow, but it should remain skill-driven and honest about scope.
- Story 1.5 established the source-of-truth/runtime-skill boundary: authored skill behavior lives in `skill_sources/`, and `auto-bean init` materializes installed runtime skills into `.agents/skills/` inside the generated workspace.
- Story 1.4 established the generated runtime workspace, `ledger.beancount` as the stable validation/Fava entrypoint, `statements/raw/` as the raw statement boundary, and `.auto-bean/` as governed runtime state. This story adds `statements/parsed/` as the parsed statement boundary and `statements/import-status.yml` as the parse-state index.

### Git Intelligence

- Recent commits show Story 1 completion work bundled story/sprint artifacts with implementation updates. Keep sprint/story status synchronized with implementation when Story 2.1 is developed.
- HEAD was `4331b1c retro epic1` on `develop` when Story 2.1 was first created. Story 2.1 starts the next epic after Epic 1 was marked done.
- The worktree was clean before Story 2.1 was originally created; this rewrite intentionally edits the Story 2.1 artifact and sprint timestamp only.

### Latest Technical Information

- Docling CLI documentation shows local conversion from the terminal, including `docling document.pdf --output scratch/ --to md` and `docling document.pdf --to json --to html --to doctags`. Source: https://context7.com/docling-project/docling/llms.txt
- Docling `v2` documentation shows directory conversion and JSON export, including `docling ./input/dir --from pdf --from docx --to md --to json --output ./scratch`. Source: https://github.com/docling-project/docling/blob/main/docs/v2.md
- Docling supported formats guidance includes PDF, XLSX, HTML, and CSV inputs. Source: https://github.com/docling-project/docling/blob/main/docs/usage/supported_formats.md
- Docling installation guidance documents `pip install docling` and Python 3.10+ support. Source: https://github.com/docling-project/docling/blob/main/README.md
- Codex subagent docs state that Codex can spawn specialized agents in parallel and collect their results, and that subagents are useful for highly parallel complex tasks. Source: https://developers.openai.com/codex/subagents
- This story no longer requires latest Pydantic guidance unless the implementation chooses to encode the parse-output contract as a Python validation helper.

### References

- [Epic breakdown](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/epics.md)
- [Architecture](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/architecture.md)
- [PRD](/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/prd.md)
- [Sprint status](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/sprint-status.yaml)
- [Story 1.6](/Users/sam/Projects/auto-bean/_bmad-output/implementation-artifacts/1-6-deliver-the-codex-first-quickstart-for-first-meaningful-use.md)
- [README](/Users/sam/Projects/auto-bean/README.md)
- [Workspace agents guide](/Users/sam/Projects/auto-bean/workspace_template/AGENTS.md)
- [Init workflow](/Users/sam/Projects/auto-bean/src/auto_bean/init.py)
- [Apply skill source](/Users/sam/Projects/auto-bean/skill_sources/auto-bean-apply/SKILL.md)
- [Mutation pipeline](/Users/sam/Projects/auto-bean/skill_sources/shared/mutation-pipeline.md)
- [Mutation authority matrix](/Users/sam/Projects/auto-bean/skill_sources/shared/mutation-authority-matrix.md)
- [Docling README](https://github.com/docling-project/docling/blob/main/README.md)
- [Docling v2 CLI docs](https://github.com/docling-project/docling/blob/main/docs/v2.md)
- [Docling supported formats](https://github.com/docling-project/docling/blob/main/docs/usage/supported_formats.md)
- [Codex subagents](https://developers.openai.com/codex/subagents)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story 2.1 originally created on 2026-04-07 from the first backlog story in `sprint-status.yaml`.
- Story 2.1 rewritten on 2026-04-07 to delegate document parsing to installed OpenAI curated `pdf` and `spreadsheet` skills/plugins instead of adding bespoke Python parsing code.
- Story 2.1 updated on 2026-04-07 to require import-skill support for sub-agent parallel parsing, raw-statement discovery, and targeted re-parse.
- Story 2.1 updated on 2026-04-07 to require `statements/import-status.yml` as the durable status index for raw statement parsing.
- Story 2.1 amended on 2026-04-11 to replace curated PDF/spreadsheet skill dependencies with a Docling CLI-based normalization workflow.
- Story 2.1 amended on 2026-04-11 to require Docling CLI installation during `auto-bean init`, not deferred installation at first import.
- Parse-output location changed from `.auto-bean/artifacts/` to `statements/parsed/`.
- No UX artifact or `project-context.md` was present, so trust-sensitive guidance was synthesized from the PRD, architecture, Epic 2, previous Epic 1 story outputs, current repo structure, and the Docling CLI documentation.
- Implemented Docling installation and runtime readiness validation during `auto-bean init`, including a dedicated runnable check for `./.venv/bin/docling`.
- Added the authored `auto-bean-import` skill with runtime metadata plus reference contracts for normalized parsed output JSON and import status YAML.
- Added workspace template support for `statements/parsed/` and `statements/import-status.yml`, and updated runtime guidance plus README copy to describe the new statement normalization boundary truthfully.
- Added verification coverage for workspace materialization, Docling readiness, and the authored import skill contract.

### Completion Notes List

- Reworked Story 2.1 around Docling CLI-driven document parsing, workspace dependency installation, sub-agent parallel parsing, `statements/import-status.yml` status tracking, raw-statement discovery, targeted re-parse, and `statements/parsed/` parse-output persistence.
- Bootstrapped generated workspaces with the `docling` CLI and failed closed when Docling is not runnable from the workspace-local runtime.
- Authored the `auto-bean-import` skill and example contracts instead of adding bespoke parsing modules under `src/auto_bean/`.
- Updated product and workspace documentation to describe the normalized import workflow and its trust boundaries.
- Verified the implementation with `uv sync --group dev`, `uv run ruff check`, `uv run ruff format`, `uv run mypy`, and `uv run pytest`.

### File List

- _bmad-output/implementation-artifacts/2-1-import-statement-files-into-a-normalized-intake-workflow.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- README.md
- skill_sources/auto-bean-import/SKILL.md
- skill_sources/auto-bean-import/agents/openai.yaml
- skill_sources/auto-bean-import/references/import-status.example.yml
- skill_sources/auto-bean-import/references/parsed-statement-output.example.json
- src/auto_bean/cli.py
- src/auto_bean/init.py
- src/auto_bean/smoke.py
- tests/test_import_skill_contract.py
- tests/test_package_foundation.py
- tests/test_setup_diagnostics.py
- workspace_template/AGENTS.md
- workspace_template/statements/import-status.yml
- workspace_template/statements/parsed/.gitkeep

## Change Log

- 2026-04-11: Implemented Story 2.1 by adding Docling-backed workspace bootstrap/readiness checks, the authored `auto-bean-import` skill and contract references, new workspace statement parse-state assets, and verification coverage for the new runtime boundary.

## Status

review
