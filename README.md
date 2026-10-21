# Auto Bean

Auto Bean is a local-first Codex plugin for initializing and operating Git-backed Beancount ledgers. Install the plugin once; use it across your ledgers. Refresh it through Codex to receive product updates.

## Install

Requirements: macOS or Linux, [uv](https://docs.astral.sh/uv/getting-started/installation/), Git, and Codex with plugin support. The plugin manages Python 3.13 and a locked base runtime for Beancount, Beanquery, Fava, Beanprice, and state validation. Statement processing prepares a separate extraction runtime with Docling and CPU dependencies on first use. Initial preparation needs network access; extraction may download substantial dependencies and PDF model files. Context7 is optional.

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

The process and categorize skills support import stages. Workers return proposed status updates; import alone writes the status index. Parsing and categorization can run in parallel, while all ledger writes are serialized. Imports review the mappings and postings in parsed JSON, obtain approval, write those transactions directly, and validate every source row plus available closing balances. Import owns final approval and statement completion. Direct transaction requests keep their conversation review behavior. Nothing is pushed automatically.

Ask Codex to validate the ledger or open Fava through the plugin launcher. All runtime tools use the selected ledger as their working directory. The plugin location is discovered from its installed skills and is never saved in ledger files.

## Import review panel

New import sessions use a local MCP side panel. Open the session from the import conversation to inspect YAML-derived statement status, extracted accounts/balances, mappings, transaction postings, inline suggestions and price results. Corrections are saved only if the underlying content still matches, so an intervening agent or user edit produces a conflict instead of being overwritten. Approval confirms the current reviewed data. Corrections update existing inline fields and resume the same conversation; if continuation fails, retry sending it without resaving the correction.

Use **Export HTML** to save a self-contained, read-only review under the selected ledger's `.auto-bean/exports/` directory. It includes every saved transaction, balances, suggestions/answers, price results, current approval and ledger validation for that session, with a capture timestamp. Open or copy the saved file to keep the review offline. Unsaved edits and raw statement attachments are excluded. Harbor import evaluations retain an HTML review for each executed step, including a clearly labelled unavailable page when no valid review exists.

The plugin runs a bundled stdio process and serves bundled UI resources through the host bridge. It requires no hosted service or local HTTP listener. Initial dependency preparation uses a plugin-managed user cache; ledger tools retain their workspace runtimes. End users do not need Node.

Durable state is limited to the existing status YAML, one parsed review JSON per statement and one session JSON. Existing imports, completed statements and their artifacts are not migrated. Status YAML keeps its current version; only new entries gain an optional workflow discriminator. Any future structural status migration belongs to the migration skill.

Parsed statements contain extracted facts and inline review decisions. Write uses those parsed postings directly. The session contains statement membership and price runs only. Optional panel approval and generated validation belong to the reviewed statement or price run; chat approval stays in the conversation. Agents edit source facts, decisions, membership, prices and lifecycle state with normal file tools. One validation operation checks review readiness or the written result; there is no transaction copy or event log in the session. The [single parsed example](plugins/auto-bean/references/parsed-statement-output.example.json) demonstrates accounts, splits, transfers and suggestions.

The [Memory skill](plugins/auto-bean/skills/auto-bean-memory/SKILL.md) derives reusable import learning from accepted decisions and validated ledger evidence. It also handles standalone inspect/update/correct/forget requests. Structured hints live in `.auto-bean/memory/*.json`; the main thread maintains reusable workspace context in `.auto-bean/memory/MEMORY.md`. Parsed/session documents contain no separate memory proposal or completion block.

See [implementation and acceptance evidence](docs/import-review-implementation.md) for the tested boundaries.

## Existing ledgers

Enable the plugin in your existing workspace and ask:

```text
Use $auto-bean:auto-bean-migrate to review and migrate this ledger.
```

Migration inventories changes before requesting approval. It backs up retired auto-bean skills, known helper scripts, and replaced documentation outside skill discovery. Customized files are identified for review. Financial files, statement evidence, import state, memory, Git history, Codex configuration, unrelated skills/scripts, unknown files inside shared folders, and the old `.venv` are preserved. Only manifest-owned skill/reference paths are retired; customized contents at those paths are reviewed and backed up.

Backups and a resumable journal live under `.auto-bean/migrations/`. Migration does not commit or push. Review customizations before deciding how to carry them forward. Do not run the retired updater after migration.

## Updates and recovery

Use Codex's plugin refresh flow. Git marketplace refresh is also available with:

```sh
codex plugin marketplace upgrade auto-bean
```

Use a fresh chat after refresh if the current chat still exposes an older plugin release; reload or reinstall through Codex if needed. Host refresh behavior varies by supported client, so marketplace refresh alone is not a claim that an already-running chat has switched versions.

Each ledger automatically prepares the runtime required by the loaded plugin. Base and extraction dependency generations live separately in gitignored `.auto-bean/runtime/<fingerprint>/` environments; failed preparation of a new generation preserves previous ones. Cloned ledgers recreate their runtime on demand. Ordinary releases do not overwrite ledger data, memory, or workspace documentation. Unsupported workspace formats stop with a compatibility diagnostic.

## Repository layout

`plugins/auto-bean/` is the directly distributable plugin and the single authored copy of its skills, references, Python helpers, locked runtime, and workspace template. There is no skill materialization step.

- `plugins/auto-bean/skills/`: canonical skills and skill-specific resources.
- `plugins/auto-bean/references/`: common guidance, import review, ledger mechanics, and machine-readable schemas/examples.
- `plugins/auto-bean/runtime/`: runtime helpers, local MCP service, launcher, and locked dependency project.
- `frontend/import-review/`: React/TypeScript source, pinned lockfile, bridge tests and reproducible bundle build.
- `plugins/auto-bean/ui/`: bundled panel and build identity; packaging rejects stale assets.
- `plugins/auto-bean/assets/workspace_template/`: ledger scaffold and stable workspace instructions.
- `.agents/plugins/marketplace.json`: the marketplace catalog.
- Root `pyproject.toml` and `uv.lock`: development tooling only.

Guidance has one owner per topic:

| Guide | Read when |
| --- | --- |
| [Common guidance](plugins/auto-bean/references/common.md) | Once per execution context for runtime, ownership, memory access and validation |
| [Import review](plugins/auto-bean/references/import-review.md) | Coordinating or contributing to an import session; use its relevant section |
| [Ledger reference](plugins/auto-bean/references/ledger-reference.md) | Unfamiliar queries, directives or commodity semantics |
| [Memory examples](plugins/auto-bean/skills/auto-bean-memory/references/memory-examples.md) | Writing or correcting a governed memory record |
| [Price reference](plugins/auto-bean/skills/auto-bean-prices/references/price-reference.md) | Selecting providers or executing/reconciling a price run |

Each skill links the common guide explicitly; task-specific guides are conditional. Plugin-level `agents/` examples define specialist roles and are not used as an assumed automatic shared-instruction mechanism. OpenAI's [conversion guidance](https://developers.openai.com/plugins/guides/submit-claude-plugin#review-what-openai-supports-1) recommends putting reusable agent procedures in skills. Skill-local `agents/openai.yaml` remains UI/invocation metadata. Repository `AGENTS.md` governs product development, not installed ledger sessions.

Run development checks:

```sh
uv sync --group dev --group eval
uv run ruff check
uv run ruff format --check
uv run mypy
uv run pytest tests evals/harbor/tests
npm --prefix frontend/import-review ci
npm --prefix frontend/import-review run build
npm --prefix frontend/import-review test
uv run python scripts/package_plugin.py --check
```

Local Python/frontend checks cover the direct-write contract and its failure cases. The obsolete Markdown-stage scenario runner has been removed; maintained evaluation fixtures live in the [Harbor suite](evals/harbor/README.md).

Harbor runs are manual and require an explicit request. Adapting its fixture/oracle/verifier code and running ordinary local tests do not run Harbor. This direct-write contract changes evaluation semantics, so historical Harbor scores apply only to their recorded builds; rerun the controls when explicitly authorized.

Run the real runtime smoke check (downloads runtime dependencies on first use):

```sh
uv run python scripts/smoke_plugin.py
```

Package the canonical plugin directory:

```sh
uv run python scripts/package_plugin.py
```

This creates a deterministic archive in `dist/`, excluding caches and including the authored plugin resources. Version tags run checks on macOS and Linux, run the real runtime smoke scenario, and attach the archive to a GitHub release. Bump the plugin and runtime project versions together before tagging a release.
