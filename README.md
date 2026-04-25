# auto-bean

`auto-bean` creates a local, Git-backed Beancount ledger workspace designed to be operated through Codex skills.

The product repo contains the installer, workspace template, and authored skill behavior. Your generated workspace contains the real ledger, raw statements, parsed evidence, governed memory, installed runtime skills, and review history.

The current scope is intentionally local-first and Codex-first. There is no public SDK or hosted service.

## Quick Start

### Requirements

- macOS
- Python `>=3.13,<3.14`
- [`uv`](https://docs.astral.sh/uv/)
- Git
- Codex as the coding agent for the generated workspace

`auto-bean init` installs a workspace-local runtime with Beancount, Fava, and Docling. It fails closed if the platform, tools, template assets, skill assets, generated ledger, Fava runtime, or Docling runtime are not ready.

### Install

From this product repository:

```bash
uv tool install --from . --force auto-bean
```

That installs the `auto-bean` CLI from the local checkout.

### Init Ledger Workspace

Create a separate runtime workspace:

```bash
auto-bean init my-ledger
```

When prompted for the coding agent, choose the default:

```text
Codex
```

Then enter the workspace:

```bash
cd ../my-ledger
```

Validate the fresh ledger:

```bash
./scripts/validate-ledger.sh
```

Open it in Fava:

```bash
./scripts/open-fava.sh
```

### First Import

Put bank, card, or account statements in:

```text
statements/raw/
```

Then ask Codex from inside the generated workspace:

```text
$auto-bean-import
```

The dollar-sign prefix matters: it tells Codex to use the installed `auto-bean-import` skill as the import entrypoint.

The import workflow discovers new or stale statement files, parses supported raw files into `statements/parsed/`, proposes ledger updates, validates the ledger, surfaces reconciliation findings, collects governed memory suggestions, and stops for user approval before finalizing accepted ledger history.

## Skill Set

Runtime skills are installed into the generated workspace under `.agents/skills/`.

### `auto-bean-query`

Read-only Beancount analysis. Use it for balances, account activity, registers, date windows, transaction existence checks, duplicate checks, and other ledger reads.

### `auto-bean-write`

Transaction drafting, correction, and transaction-specific validation. Higher-level workflows use this when they need to write or repair Beancount entries.

### `auto-bean-import`

The user-facing statement import workflow. Start here when importing statements from `statements/raw/`.

Use it with:

```text
$auto-bean-import
```

### `auto-bean-process`

Internal import stage. It handles raw-to-parsed statement processing, Docling-backed extraction, parsed artifacts, status updates, and first-seen account structure when evidence is strong enough.

Users normally should not call this directly. `auto-bean-import` delegates to it.

### `auto-bean-apply`

Internal apply and reconciliation stage. It turns reviewed parsed evidence into candidate ledger postings, validates outcomes, tracks review status, and presents finalization details.

Users normally should not call this directly. `auto-bean-import` delegates to it.

### `auto-bean-memory`

Governed memory persistence for approved reusable decisions such as account mappings, categorization patterns, transfer detection behavior, naming conventions, import-source behavior, deduplication decisions, and clarification outcomes.

Workflows may suggest memory. Only this skill should write `.auto-bean/memory/**`.

## CLI Commands

### `auto-bean init <PROJECT-NAME>`

Creates a new ledger workspace. It copies the workspace template, installs managed skills, initializes Git, creates a workspace-local `.venv`, validates `ledger.beancount`, verifies Fava and Docling, and creates an initial commit.

Useful options:

```bash
auto-bean init my-ledger --verbose
auto-bean init my-ledger --json
```

### `auto-bean update [WORKSPACE]`

Updates managed workspace files from the current packaged product assets.

It updates:

- `AGENTS.md`
- managed files under `.agents/skills/`

It does not overwrite:

- `ledger.beancount`
- `beancount/`
- `.auto-bean/`

Check what would change:

```bash
auto-bean update . --check
```

Apply updates:

```bash
auto-bean update .
```

Useful options:

```bash
auto-bean update . --verbose
auto-bean update . --json
auto-bean update . --check --json
```

## Workspace Scripts

Generated workspaces include helper scripts under `scripts/`.

### Beancount Validation

```bash
./scripts/validate-ledger.sh
```

Equivalent direct command:

```bash
./.venv/bin/bean-check ledger.beancount
```

### Fava

```bash
./scripts/open-fava.sh
```

Equivalent direct command:

```bash
./.venv/bin/fava ledger.beancount
```

## Workspace Tree

A generated workspace looks like this:

```text
my-ledger/
|-- AGENTS.md
|-- ledger.beancount
|-- beancount/
|   |-- accounts.beancount
|   `-- opening-balances.beancount
|-- statements/
|   |-- raw/
|   |-- parsed/
|   `-- import-status.yml
|-- .auto-bean/
|   |-- artifacts/
|   |-- proposals/
|   `-- memory/
|       |-- account_mappings.json
|       |-- category_mappings.json
|       |-- clarification_outcomes.json
|       |-- deduplication_decisions.json
|       |-- naming_conventions.json
|       |-- transfer_detection.json
|       `-- import_sources/
|           `-- index.json
|-- .agents/
|   `-- skills/
|       |-- auto-bean-query/
|       |-- auto-bean-write/
|       |-- auto-bean-import/
|       |-- auto-bean-process/
|       |-- auto-bean-apply/
|       `-- auto-bean-memory/
|-- scripts/
|   |-- validate-ledger.sh
|   `-- open-fava.sh
`-- .venv/
```

Important boundaries:

- `ledger.beancount` is the stable ledger entrypoint.
- `beancount/` contains included ledger fragments.
- `statements/raw/` contains source statement files.
- `statements/parsed/` contains normalized statement evidence, not accepted ledger history.
- `statements/import-status.yml` tracks parse and import state.
- `.auto-bean/artifacts/` stores diagnostics and audit artifacts.
- `.auto-bean/memory/` stores approved reusable workflow memory.
- `.agents/skills/` contains installed runtime skills.

## For Developers

### Under-the-Hood Workflow

`auto-bean` separates product authoring from ledger operation:

- This repo authors the CLI, workspace scaffold, and skill behavior.
- `auto-bean init` materializes those assets into a user-owned workspace.
- The generated workspace is a Git repo with a first valid Beancount ledger and an initial commit.
- Codex skills are the primary user interface after initialization.

The import workflow is staged:

1. `$auto-bean-import` inspects `statements/raw/`, `statements/parsed/`, and `statements/import-status.yml`.
2. New or stale supported files are assigned to processing work.
3. `$auto-bean-process` normalizes raw `.pdf`, `.csv`, `.xlsx`, and `.xls` statements into parsed JSON evidence.
4. Parsed statement evidence is handed to `$auto-bean-apply`.
5. `$auto-bean-apply` uses `auto-bean-query` for ledger reads and `auto-bean-write` for transaction drafting or correction.
6. The workflow validates the ledger, reports warnings and reconciliation findings, shows changed files and diff context, and waits for user approval before finalization.

Memory is governed:

- Workflows can propose reusable decisions.
- Memory suggestions are advisory and must stay separate from raw statements, parsed dumps, diagnostics, and ledger entries.
- `auto-bean-memory` validates and persists approved reusable decisions.
- Other skills should read memory according to the shared memory access rules, but should not write `.auto-bean/memory/**` directly.

Review boundaries are deliberate:

- Parsed facts are evidence.
- Ledger edits are candidate mutations.
- Reused memory is guidance, not silent authority.
- Validation and review happen before commit or push.
- Recovery is expected to use Git history instead of overwriting accepted state.

### Toolset

Runtime and development tools:

- Python `>=3.13,<3.14`
- `uv` for local environments, scripts, and installs
- Click for the CLI
- Rich for CLI progress rendering
- Beancount for ledger validation and query mechanics
- Fava for ledger inspection
- Docling for statement extraction support
- Ruff for linting and formatting
- mypy for strict type checks
- pytest for tests
- Git for workspace history and recovery

Use the local dev environment:

```bash
uv sync --group dev
```

Run checks after code changes:

```bash
uv run ruff check
uv run ruff format
uv run mypy
uv run pytest
```

Optional smoke checks:

```bash
uv run python scripts/run_smoke_checks.py
```

### Repo Tree

The product repository is organized around a small Python package plus authored workspace assets:

```text
auto-bean/
|-- AGENTS.md
|-- README.md
|-- LICENSE
|-- pyproject.toml
|-- uv.lock
|-- src/
|   `-- auto_bean/
|       |-- __init__.py
|       |-- __main__.py
|       |-- cli.py
|       |-- init.py
|       |-- smoke.py
|       `-- py.typed
|-- skill_sources/
|   |-- auto-bean-query/
|   |-- auto-bean-write/
|   |-- auto-bean-import/
|   |-- auto-bean-process/
|   |-- auto-bean-apply/
|   |-- auto-bean-memory/
|   `-- shared/
|-- workspace_template/
|   |-- AGENTS.md
|   |-- ledger.beancount
|   |-- beancount/
|   |-- statements/
|   `-- .auto-bean/
|-- scripts/
|   `-- run_smoke_checks.py
`-- tests/
    `-- test_memory_assets.py
```

Development boundaries:

- Keep the CLI thin and support-oriented.
- Keep the end-to-end bootstrap and update workflow in `src/auto_bean/init.py`.
- Author skill behavior in `skill_sources/` first.
- Treat `workspace_template/` as scaffold only.
- Do not add live installed runtime skills to the product repo `.agents/skills/`.
- Prefer changing skill markdown behavior before adding new Python surfaces.
