# auto-bean

`auto-bean` is a packaged Python foundation for local-first coding-agent workflows around Beancount ledgers.

The repo now includes a macOS-only installation path based on `uv tool install` plus an interactive `init <PROJECT-NAME>` workflow for creating a fresh runtime ledger workspace.

Baseline repository verification now lives in CI and is reproducible locally with Ruff, mypy, pytest, and deterministic smoke checks.

## Supported scope

- supported platform: macOS only
- install target: `uv` tool named `auto-bean`
- supported workspace creation surface: `auto-bean init <PROJECT-NAME>`

## Commands

Install from the product repo:

```bash
uv tool install --from . --force auto-bean
```

Verify after install, even before your shell PATH is updated:

```bash
uv tool run --from . auto-bean readiness
```

Verify through the installed command once it is on `PATH`:

```bash
auto-bean readiness
```

Render machine-readable diagnostics:

```bash
auto-bean readiness --json
```

Human-readable runs also print a stable `run_id` and the governed artifact path for the workflow result.

Create a base ledger workspace:

```bash
auto-bean init my-ledger
```

The init workflow asks which coding agent to target. Only `Codex` is supported right now.

Successful init creates a sibling runtime workspace with:

- `ledger.beancount` as the stable entrypoint
- `AGENTS.md` for workspace operating guidance
- a `.git/` repository so workspace changes can be reviewed and versioned immediately
- an initial Git commit containing the generated scaffold and helper files
- `beancount/`, `statements/raw/`, `docs/`, `.auto-bean/`, and `.agents/skills/`
- a workspace-local `.venv` with `beancount` and `fava` installed automatically
- helper scripts under `scripts/` for validation and Fava launch using the workspace-local runtime
- authored skills copied from `skill_sources/` into the new workspace runtime

The command output includes the created workspace path, a manifest of generated files, validation status, and next-step commands.

## Remediation behavior

- if `uv` is missing, readiness fails with guidance to install `uv` and then run the install command
- if the machine is not macOS, the command fails closed instead of attempting partial support
- if the tool installs but the shell cannot find `auto-bean`, verify first with `uv tool run --from . auto-bean readiness`, then follow the reported `PATH` remediation
- installation uses `uv tool install --from` rather than ad hoc global Python mutation or `sudo pip`
- `init <PROJECT-NAME>` fails closed when the project name is unsafe, the destination already exists and is non-empty, the workspace template is incomplete, or the requested coding agent is unsupported
- `init <PROJECT-NAME>` bootstraps a workspace-local `.venv`, installs `beancount` and `fava`, validates the generated `ledger.beancount`, and checks that Fava is runnable before reporting success
- `init <PROJECT-NAME>` fails closed if the authored skill sources required for runtime installation are missing

## Repository baseline checks

Keep local verification aligned with CI:

```bash
uv sync --group dev
uv run ruff check src tests scripts
uv run mypy src tests scripts
uv run pytest
uv run python scripts/run_smoke_checks.py
```

Workflow diagnostics are persisted under `.auto-bean/artifacts/` so maintainers can inspect validation outcomes, blocked flows, and troubleshooting context without scraping stack traces.

## Workspace use

After `auto-bean init my-ledger`, move into the created workspace and use:

```bash
cd ../my-ledger
./.venv/bin/bean-check ledger.beancount
./.venv/bin/fava ledger.beancount
```

The generated helper scripts provide the same entrypoints:

```bash
./scripts/validate-ledger.sh
./scripts/open-fava.sh
```

For trust-sensitive structural edits, prefer the installed workspace skill under `.agents/skills/auto-bean-apply/`. The product repo authors that behavior in `skill_sources/`, and `auto-bean init` materializes the installed runtime copy into the generated workspace.

## Repo boundaries

- application code belongs under `src/auto_bean/`
- stable user-owned ledger, memory, statement, and artifact state belongs in the generated workspace, not in the product repo
- `skill_sources/` owns authored skill behavior in the product repo
- `.agents/skills/` remains the home for installed skill surfaces inside the generated workspace
- future governed runtime state belongs under the workspace-local `.auto-bean/`, not inside the package tree
- `workspace_template/` in this repo is the authored source of truth for new workspace scaffolding
