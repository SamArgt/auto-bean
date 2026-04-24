# auto-bean

`auto-bean` is a local-first, Codex-first foundation for Beancount ledger workflows.

Right now this repository gives you a supported first session for:

- installing `auto-bean` from this product repo
- creating a separate runtime ledger workspace
- validating `ledger.beancount`
- inspecting that ledger in Fava
- querying ledger balances, account activity, registers, and existing transactions through the read-only `auto-bean-query` skill
- drafting and validating Beancount transaction entries through the focused `auto-bean-write` skill
- normalizing supported statement files into inspectable parsed outputs through a workspace skill
- creating or extending first-seen ledger account structure directly from imported statement evidence, then reviewing parsed statement facts, derived ledger edits, validation output, and the diff together before commit or push
- turning reviewed normalized statement evidence into candidate Beancount postings through a separate apply workflow, with advisory reuse of repeated-import source context and the same commit-gated review boundary
- surfacing likely transfers, possible duplicates, and unbalanced or currency-risk outcomes as explicit review findings before finalization
- pausing ambiguous or unfamiliar reconciliation outcomes to ask the user a bounded clarification question before any risky interpretation is applied
- persisting approved reusable decisions through governed local memory under `.auto-bean/memory/`
- explaining committed recovery through git-backed revert guidance

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

### 2. Create your runtime ledger workspace

Create a new workspace next to this product repo:

```bash
auto-bean init my-ledger
```

`init` asks which coding agent should back the workspace. Only `Codex` is supported right now.

On success, `auto-bean` creates a separate runtime Git repository with:

- `ledger.beancount` as the stable ledger entrypoint
- `beancount/` for included ledger fragments
- `beancount/accounts.beancount` for durable account `open` directives
- `statements/raw/` for statement files that later import stories will process
- `.auto-bean/` for governed runtime artifacts and diagnostics
- `.auto-bean/memory/` for governed runtime memory that stores approved reusable decisions
  - one JSON file per non-import memory category
  - `import_sources/index.json` plus one source file per import source
- `.agents/skills/` for installed runtime skills
  - `auto-bean-query` for read-only ledger analysis
  - `auto-bean-write` for transaction drafting and validation
  - `auto-bean-import` for statement normalization and evidence handoff
  - `auto-bean-apply` for reviewed structural mutation orchestration and finalization
  - `auto-bean-memory` for governed persistence of approved reusable decisions
- `AGENTS.md` for workspace operating guidance
- a workspace-local `.venv` with `beancount`, `fava`, and `docling`
- `scripts/validate-ledger.sh` and `scripts/open-fava.sh`
- `statements/parsed/` for normalized statement parse outputs
- `statements/import-status.yml` for durable statement parse state

This matters operationally: the product repo is where `auto-bean` is authored, while the generated workspace is where your live ledger, statements, and governed runtime state live.

If `uv` is missing or the machine is unsupported, `auto-bean init` fails immediately with structured remediation details instead of sending you through a separate readiness command.
If the workspace-local Docling CLI cannot be installed or is not runnable, `auto-bean init` also fails closed instead of claiming statement intake is ready.

### 3. Move into the workspace and validate the ledger

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

### 4. Inspect the ledger in Fava

Open the generated ledger in Fava with either the helper script or the direct command:

```bash
./scripts/open-fava.sh
./.venv/bin/fava ledger.beancount
```

This is the supported inspection path today.

### 5. Use Codex-first workflows inside the workspace

Once you are in the generated workspace, treat Codex and the installed skills as the primary workflow surface.

For read-only ledger analysis, use:

```text
.agents/skills/auto-bean-query/
```

For transaction drafting, correction, and transaction-specific validation, use:

```text
.agents/skills/auto-bean-write/
```

For trust-sensitive structural ledger changes and finalization orchestration, use the installed runtime skill under:

```text
.agents/skills/auto-bean-apply/
```

That runtime skill is materialized into the workspace during `auto-bean init`. In this product repo, the authored source of truth for that behavior lives under `skill_sources/`.

### 6. Normalize statements through the installed import skill

Statement intake is now a supported skill-driven workflow inside the generated workspace.

Use the installed runtime skill under:

```text
.agents/skills/auto-bean-import/
```

That workflow uses the workspace-local Docling CLI to normalize supported `PDF`, `CSV`, and Excel statement files from `statements/raw/` into inspectable JSON outputs under `statements/parsed/`, then, when the imported evidence is strong enough, extend ledger account structure directly in the workspace before presenting a single review surface that shows parsed statement facts, derived ledger edits, validation output, and the diff together.

When import decisions require ledger analysis, `auto-bean-import` relies on `auto-bean-query` instead of manually approximating balances, activity, register rows, or transaction existence from file scans. When reviewed normalized evidence is ready to become transaction postings, `auto-bean-import` hands that evidence to `auto-bean-apply`; `auto-bean-apply` then relies on `auto-bean-query` for ledger reads and `auto-bean-write` for transaction drafting or correction.

The durable boundaries for this workflow are:

- `statements/raw/`: raw source statements
- `statements/parsed/`: normalized parse outputs only
- `statements/import-status.yml`: parse-state index for new, stale, blocked, failed, or parsed files
- `.agents/skills/auto-bean-import/`: installed runtime skill for statement intake orchestration
- `.agents/skills/auto-bean-query/`: installed foundation skill for read-only ledger analysis
- `.agents/skills/auto-bean-write/`: installed foundation skill for transaction drafting and validation


That review surface should make these distinctions obvious:

- parsed statement facts under `statements/parsed/` and `statements/import-status.yml` are inspectable evidence, not accepted ledger history
- reused governed memory hints under `.auto-bean/memory/` are advisory guidance, not silent authority
- derived ledger edits under `ledger.beancount` or `beancount/**` are the candidate mutation produced from that evidence
- reconciliation findings make the workflow's suggested action visible, but the user still decides what happens to each finding
- warnings, blocked inferences, and `git diff` appear before any finalization request
- the user can stop, defer, or reject finalization without corrupting prior accepted ledger history
- committed recovery is explained as reverting the recorded commit, not silently overwriting ledger state

The boundaries that matter now are:

- `ledger.beancount`: stable ledger entrypoint
- `beancount/`: included ledger files
- `beancount/accounts.beancount`: preferred location for account `open` directives
- `statements/raw/`: where raw statement files land
- `statements/parsed/`: where normalized parse outputs are written
- `statements/import-status.yml`: where parse-state tracking lives
- `.auto-bean/`: governed runtime artifacts and workflow state
- `.auto-bean/memory/`: governed runtime memory for approved reusable decisions
- `.agents/skills/auto-bean-query/`: installed foundation skill for read-only Beancount ledger analysis
- `.agents/skills/auto-bean-write/`: installed foundation skill for transaction drafting, correction, and validation
- `.agents/skills/auto-bean-import/`: installed skill for Docling-driven statement normalization, first-seen account mutation, and reviewed evidence handoff
- `.agents/skills/auto-bean-apply/`: installed skill for turning reviewed evidence into candidate transaction postings or other reviewed structural mutations
- `.agents/skills/auto-bean-memory/`: installed skill for validating and persisting approved reusable workflow decisions

## Failure and remediation behavior

- If `uv` is missing, `auto-bean init <PROJECT-NAME>` fails with installation guidance.
- If the machine is not macOS, the workflow fails closed rather than pretending partial support exists.
- `auto-bean init <PROJECT-NAME>` fails closed when the project name is unsafe, the destination already exists and is non-empty, the workspace template is incomplete, or the requested coding agent is unsupported.
- `auto-bean init <PROJECT-NAME>` validates the generated `ledger.beancount` and checks that both Fava and Docling are runnable before it reports success.
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

Workflow diagnostics are persisted under `.auto-bean/artifacts/` so maintainers can inspect validation outcomes and troubleshooting context without scraping stack traces. Approved reusable decisions live separately under governed runtime memory, not in ledger files or ad hoc statement-side artifacts.
