# Auto Bean

Auto Bean is a Codex plugin for managing local, Git-backed [Beancount](https://beancount.github.io/) ledgers. It initializes ledgers, imports statements, reviews transactions, updates prices, and remembers accepted decisions. You review and approve financial changes before they are written.

## Install

Requirements: macOS or Linux, Git, [uv](https://docs.astral.sh/uv/getting-started/installation/), and Codex with plugin support.

```sh
codex plugin marketplace add SamArgt/auto-bean
codex plugin add auto-bean@auto-bean
```

The plugin prepares its locked Python runtime on first use. Statement extraction also downloads PDF models. Initial setup needs network access; no separate API key or Node.js installation is required.

To update, refresh the plugin in Codex or run `codex plugin marketplace upgrade auto-bean`. Open a fresh chat after refreshing.

## Use

Open an empty ledger directory in Codex and ask:

```text
Use $auto-bean:auto-bean-init to initialize a ledger here.
```

For daily work, open the ledger directory with the plugin enabled:

| Task | Skill |
| --- | --- |
| Import statements placed in `statements/raw/` | `$auto-bean:auto-bean-import` |
| Query balances and transactions | `$auto-bean:auto-bean-query` |
| Add or correct transactions | `$auto-bean:auto-bean-write` |
| Update commodity prices | `$auto-bean:auto-bean-prices` |
| Inspect or update reusable decisions | `$auto-bean:auto-bean-memory` |
| Review and migrate an existing ledger | `$auto-bean:auto-bean-migrate` |

Imports resume unfinished work, request missing input, and validate source rows and available closing balances after writing. Nothing is pushed automatically. You can also ask Codex to validate the ledger or open Fava.

The import review panel has **Session**, **Account**, and **Price** views. Save corrections, then select **Send saved changes** to continue the import. **Export HTML** saves a read-only snapshot. Conversation review remains available if the panel cannot open. See the [review implementation guide](docs/import-review-implementation.md) for details.

## Develop

Follow [AGENTS.md](AGENTS.md). Author skills in the plugin directory; ledger workspaces use the installed plugin. The root Python environment contains development tools. The plugin runtime has its own dependency lock.

| Path | Contents |
| --- | --- |
| `plugins/auto-bean/` | Distributable plugin: skills, references, runtime, workspace template, and bundled UI |
| `frontend/import-review/` | React/TypeScript UI source and tests |
| `tests/` | Product tests |
| `evals/harbor/` | Evaluation tasks, verifiers, configuration, and run guide |
| `scripts/` | Package validation, archive creation, and runtime smoke check |
| `docs/` | Implementation details |

### Setup and checks

Developers also need Node.js. Harbor runs need Docker with Compose.

```sh
uv sync --group dev --group eval
npm --prefix frontend/import-review ci

uv run --group eval ruff check
uv run --group eval ruff format --check
uv run --group eval mypy
uv run --group eval pytest tests evals/harbor/tests

npm --prefix frontend/import-review run build
npm --prefix frontend/import-review test
uv run python scripts/package_plugin.py --check
```

Rebuild the UI after frontend changes. Packaging rejects a stale bundle.

```sh
uv run python scripts/smoke_plugin.py   # Runtime smoke check; may download dependencies
uv run python scripts/package_plugin.py # Create the archive in dist/
```

### Parsed schemas

Each import group has one saved JSON file. Its `statements[]` entries hold the source facts and inline review.

| Schema | Role |
| --- | --- |
| `plugins/auto-bean/references/schemas/parsed-group.schema.json` | Validates the saved group and its statement entries. |
| `plugins/auto-bean/references/schemas/parsed-statement.schema.json` | Defines one statement entry. Edit this source contract directly. |

After editing the statement contract, run `uv run python scripts/build_review_schemas.py`. This regenerates the group, session and status schemas. The group embeds the statement contract for offline validation. Session price runs reuse its approval and validation fields. Tests check that generated schemas match their sources.

Parsed documents still use `schema_version: 2`. The plugin no longer accepts the old v1 parsed format. This cleanup does not migrate saved workspace files.

### Harbor evaluations

Run evaluations only when explicitly requested. The configured suite uses the current checkout and existing Codex sign-in. Use one concurrent trial when Docker has only 8 GiB of memory.

```sh
export PYTHONPATH="$PWD"
export CODEX_FORCE_AUTH_JSON=1
uv run --group eval harbor run --config evals/harbor/codex.yaml \
  --n-concurrent 1 --jobs-dir "$PWD/.cache/harbor/jobs"
```

Inspect per-step rewards and errors in the saved results. See the [Harbor guide](evals/harbor/README.md) for task selection, controls, authentication, and artifacts.
