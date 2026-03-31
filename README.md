# auto-bean

`auto-bean` is a packaged Python foundation for local-first coding-agent workflows around Beancount ledgers.

The repo now includes a macOS-only installation path based on `uv tool install`. Workspace creation is intentionally deferred to a later `init <PROJECT-NAME>` workflow.

Baseline repository verification now lives in CI and is reproducible locally with Ruff, mypy, pytest, and deterministic smoke checks.

## Supported scope

- supported platform: macOS only
- install target: `uv` tool named `auto-bean`
- future workspace creation surface: `auto-bean init <PROJECT-NAME>`

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

Reserved future workspace creation surface:

```bash
auto-bean init my-ledger
```

## Remediation behavior

- if `uv` is missing, readiness fails with guidance to install `uv` and then run the install command
- if the machine is not macOS, the command fails closed instead of attempting partial support
- if the tool installs but the shell cannot find `auto-bean`, verify first with `uv tool run --from . auto-bean readiness`, then follow the reported `PATH` remediation
- installation uses `uv tool install --from` rather than ad hoc global Python mutation or `sudo pip`
- `init <PROJECT-NAME>` is reserved but not implemented in this story

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

## Repo boundaries

- application code belongs under `src/auto_bean/`
- stable user-owned ledger, memory, and artifact state must stay out of `src/`
- `.agents/skills/` remains the home for installed skill surfaces
- future governed runtime state belongs under `.auto-bean/`, not inside the package tree
