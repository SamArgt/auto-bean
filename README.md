# auto-bean

`auto-bean` is a packaged Python foundation for local-first coding-agent workflows around Beancount ledgers.

The repo now includes a macOS-only bootstrap and readiness surface for preparing the product environment before later ledger workflows begin.

## Supported scope

- supported platform: macOS only
- managed environment: repo-local `uv` project environment
- required local dependencies: `auto-bean`, `beancount`, and `fava`

## Commands

Bootstrap or reconcile the repo-local environment:

```bash
uv run auto-bean bootstrap
```

Check whether the current repo-local environment is ready for later workflows:

```bash
uv run auto-bean readiness
```

Render machine-readable diagnostics:

```bash
uv run auto-bean readiness --json
```

## Remediation behavior

- if `uv` is missing, the command fails with guidance to install `uv`
- if `uv sync` falls back to a Beancount source build and the local toolchain is missing a suitable `bison`, bootstrap reports that specific remediation
- if the machine is not macOS, the command fails closed instead of attempting partial support
- if the repo-local environment or dependencies are missing, the readiness check reports the failing prerequisite and points back to `auto-bean bootstrap`
- bootstrap uses `uv sync` rather than global Python mutation or `sudo pip`

## Repo boundaries

- application code belongs under `src/auto_bean/`
- stable user-owned ledger, memory, and artifact state must stay out of `src/`
- top-level `scripts/` remains reserved for repo helper tooling
- `.agents/skills/` remains the home for installed skill surfaces
- future governed runtime state belongs under `.auto-bean/`, not inside the package tree
