# Auto Bean

Auto Bean is a local-first Codex plugin for initializing and operating Git-backed Beancount ledgers. Install the plugin once; use it across your ledgers. Refresh it through Codex to receive product updates.

## Install

Requirements: macOS or Linux, [uv](https://docs.astral.sh/uv/getting-started/installation/), Git, and Codex with plugin support. The plugin manages Python 3.13 and the locked Beancount, Beanquery, Fava, Docling, and Beanprice runtime. Initial runtime preparation needs network access and may download substantial dependencies. Context7 is optional.

Register the GitHub marketplace:

```sh
codex plugin marketplace add SamArgt/auto-bean
```

Install **Auto Bean** from that marketplace in Codex. For supported CLI versions, the equivalent is:

```sh
codex plugin add auto-bean@auto-bean
```

Open an empty ledger directory in Codex and ask:

```text
Use $auto-bean:auto-bean-init to initialize a ledger here.
```

You can also name a new directory. Setup validates the ledger and runtime and creates an initial Git commit when your identity is configured. No standalone auto-bean tool or API key is required.

## Operate a ledger

Open the ledger directory in Codex with Auto Bean enabled:

| Request | Skill |
| --- | --- |
| Import statements from `statements/raw/` | `$auto-bean:auto-bean-import` |
| Read balances, activity, or transactions | `$auto-bean:auto-bean-query` |
| Draft or correct transactions | `$auto-bean:auto-bean-write` |
| Update commodity prices | `$auto-bean:auto-bean-prices` |
| Persist eligible reusable decisions | `$auto-bean:auto-bean-memory` |

The process and categorize skills support import stages. Ledger edits remain working-tree candidates until reviewed and approved; import owns its final approval and statement completion. Nothing is pushed automatically.

Ask Codex to validate the ledger or open Fava through the plugin launcher. All runtime tools use the selected ledger as their working directory. The plugin location is discovered from its installed skills and is never saved in ledger files.

## Existing ledgers

Enable the plugin in your existing workspace and ask:

```text
Use $auto-bean:auto-bean-migrate to review and migrate this ledger.
```

Migration inventories changes before requesting approval. It backs up retired auto-bean skills, known helper scripts, and replaced documentation outside skill discovery. Customized files are identified for review. Financial files, statement evidence, import state, memory, Git history, Codex configuration, unrelated skills/scripts, and the old `.venv` are preserved.

Backups and a resumable journal live under `.auto-bean/migrations/`. Migration does not commit or push. Review customizations before deciding how to carry them forward. Do not run the retired updater after migration.

## Updates and recovery

Use Codex's plugin refresh flow. Git marketplace refresh is also available with:

```sh
codex plugin marketplace upgrade auto-bean
```

Use a fresh chat after refresh if the current chat still exposes an older plugin release; reload or reinstall through Codex if needed. Host refresh behavior varies by supported client, so marketplace refresh alone is not a claim that an already-running chat has switched versions.

Each ledger automatically prepares the runtime required by the loaded plugin. Dependency generations live in gitignored `.auto-bean/runtime/<fingerprint>/` environments; failed preparation of a new generation preserves previous ones. Cloned ledgers recreate their runtime on demand. Ordinary releases do not overwrite ledger data, memory, or workspace documentation. Unsupported workspace formats stop with a compatibility diagnostic.

## Repository layout

`plugins/auto-bean/` is the directly distributable plugin and the single authored copy of its skills, references, Python helpers, locked runtime, and workspace template. There is no skill materialization step.

- `plugins/auto-bean/skills/`: canonical skills and skill-specific resources.
- `plugins/auto-bean/references/`: shared workflow rules, schemas, and execution guidance.
- `plugins/auto-bean/runtime/`: stdlib helpers, launcher, and a dependency-only uv project.
- `plugins/auto-bean/assets/workspace_template/`: ledger scaffold and stable workspace instructions.
- `.agents/plugins/marketplace.json`: the marketplace catalog.
- Root `pyproject.toml` and `uv.lock`: development tooling only.

Run development checks:

```sh
uv sync --group dev
uv run ruff check
uv run ruff format --check
uv run mypy
uv run pytest
uv run python scripts/package_plugin.py --check
```

Run the real runtime smoke check (downloads runtime dependencies on first use):

```sh
uv run python scripts/smoke_plugin.py
```

Package the canonical plugin directory:

```sh
uv run python scripts/package_plugin.py
```

This creates a deterministic archive in `dist/`, excluding caches and including the authored plugin resources. Version tags run checks on macOS and Linux, run the real runtime smoke scenario, and attach the archive to a GitHub release. Bump the plugin and runtime project versions together before tagging a release.
