# auto-bean

`auto-bean` is a local-first, Codex-first foundation for Beancount ledger workflows.

Right now this repository gives you a supported first session for:

- installing `auto-bean` from this product repo
- checking readiness on macOS
- creating a separate runtime ledger workspace
- validating `ledger.beancount`
- inspecting that ledger in Fava
- understanding where later statement-import work will enter the workflow

It does not expose a public SDK or external API today. The stable user interface is the coding-agent workflow inside the generated workspace.

## Supported scope

- Platform: macOS only
- Install surface: `uv tool install --from . --force auto-bean`
- Workspace creation surface: `auto-bean init <PROJECT-NAME>`
- Supported coding agent during init: `Codex`

## First-session quickstart

### 1. Install from the product repo

From the root of this repository:

```bash
uv tool install --from . --force auto-bean
```

This installs the local package as the `auto-bean` tool without asking you to mutate global Python by hand.

### 2. Verify readiness

If your shell has not picked up the installed tool on `PATH` yet, verify with:

```bash
uv tool run --from . auto-bean readiness
```

Once `auto-bean` is available directly, the normal check is:

```bash
auto-bean readiness
```

For machine-readable diagnostics:

```bash
auto-bean readiness --json
```

Human-readable readiness output includes a stable `run_id` and the governed artifact path for the workflow result.

### 3. Create your runtime ledger workspace

Create a new workspace next to this product repo:

```bash
auto-bean init my-ledger
```

`init` asks which coding agent should back the workspace. Only `Codex` is supported right now.

On success, `auto-bean` creates a separate runtime Git repository with:

- `ledger.beancount` as the stable ledger entrypoint
- `beancount/` for included ledger fragments
- `statements/raw/` for statement files that later import stories will process
- `.auto-bean/` for governed runtime artifacts and proposal state
- `.agents/skills/` for installed runtime skills
- `AGENTS.md` for workspace operating guidance
- a workspace-local `.venv` with `beancount` and `fava`
- `scripts/validate-ledger.sh` and `scripts/open-fava.sh`

This matters operationally: the product repo is where `auto-bean` is authored, while the generated workspace is where your live ledger, statements, and governed runtime state live.

### 4. Move into the workspace and validate the ledger

After init finishes, change into the new workspace:

```bash
cd ../my-ledger
```

Validate the generated base ledger with either the helper script or the direct Beancount command:

```bash
./scripts/validate-ledger.sh
./.venv/bin/bean-check ledger.beancount
```

“First meaningful use” for the current V1 scope means you now have a bootstrapped workspace, a valid `ledger.beancount`, and a clear place to continue operating.

### 5. Inspect the ledger in Fava

Open the generated ledger in Fava with either the helper script or the direct command:

```bash
./scripts/open-fava.sh
./.venv/bin/fava ledger.beancount
```

This is the supported inspection path today.

### 6. Use Codex-first workflows inside the workspace

Once you are in the generated workspace, treat Codex and the installed skills as the primary workflow surface.

For trust-sensitive structural ledger changes, use the installed runtime skill under:

```text
.agents/skills/auto-bean-apply/
```

That runtime skill is materialized into the workspace during `auto-bean init`. In this product repo, the authored source of truth for that behavior lives under `skill_sources/`.

### 7. Understand what comes next

The next major operating path is statement import, but it is not exposed as a public SDK or finished import command yet.

The boundaries that matter now are:

- `ledger.beancount`: stable ledger entrypoint
- `beancount/`: included ledger files
- `statements/raw/`: where raw statement files will land
- `.auto-bean/`: governed runtime artifacts and workflow state
- `.agents/skills/auto-bean-apply/`: installed skill for reviewed structural edits

Later stories will add the normalized import and review workflows that begin from `statements/raw/`. This README intentionally does not document commands or skills that do not exist yet.

## Failure and remediation behavior

- If `uv` is missing, readiness fails with installation guidance.
- If the machine is not macOS, the workflow fails closed rather than pretending partial support exists.
- If the installed tool is not yet on `PATH`, use `uv tool run --from . auto-bean readiness` first and then apply the reported shell remediation.
- `auto-bean init <PROJECT-NAME>` fails closed when the project name is unsafe, the destination already exists and is non-empty, the workspace template is incomplete, or the requested coding agent is unsupported.
- `auto-bean init <PROJECT-NAME>` validates the generated `ledger.beancount` and checks that Fava is runnable before it reports success.
- `auto-bean init <PROJECT-NAME>` fails if the authored skill sources needed for runtime installation are missing.

## Repo boundaries

- `src/auto_bean/` contains the packaged application and thin CLI surface.
- `skill_sources/` is the source of truth for authored skill behavior in the product repo.
- `workspace_template/` is the source of truth for generated workspace scaffolding.
- The generated workspace, not this repo, owns the live ledger, imported statements, and governed runtime state.
- Installed runtime skills belong under workspace-local `.agents/skills/`, not the product-repo `.agents/skills/`.

## Maintainer checks

Keep local verification aligned with CI:

```bash
uv sync --group dev
uv run ruff check src tests scripts
uv run mypy src tests scripts
uv run pytest
uv run python scripts/run_smoke_checks.py
```

Workflow diagnostics are persisted under `.auto-bean/artifacts/` so maintainers can inspect validation outcomes and troubleshooting context without scraping stack traces.
