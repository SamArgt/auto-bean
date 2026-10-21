# Harbor workflow evaluations

The two runnable Harbor tasks live directly in `evals/harbor/tasks/`:
`init-ledger` and `import-two-statements`. Run commands from the repository root.
Requirements: Docker with Compose and uv; each task requests 2 CPUs, 8 GiB
memory, and 20 GiB storage. Runs are manual and use synthetic data only.

## Run

```sh
uv sync --group dev --group eval
export PYTHONPATH="$PWD"
export CODEX_FORCE_AUTH_JSON=1
uv run --group eval harbor run --config evals/harbor/codex.yaml --jobs-dir "$PWD/.cache/harbor/jobs"
```

This is Harbor's native CLI and configuration. The config runs both tasks using
`gpt-6.1-sol`, one attempt, one concurrent trial, the pinned Codex CLI, and your
existing Codex sign-in. The thin adapter installs the local plugin and preserves
it across native session resumption; Harbor owns execution and trajectory capture.
`PYTHONPATH` makes this local adapter importable by Harbor. No separate prepare
or build command is needed. The absolute `--jobs-dir` path avoids a Harbor 0.24
Docker Compose issue that otherwise resolves relative artifact paths against task
directories.

Run one task:

```sh
uv run --group eval harbor run -c evals/harbor/codex.yaml -p evals/harbor/tasks/init-ledger --jobs-dir "$PWD/.cache/harbor/jobs"
uv run --group eval harbor run -c evals/harbor/codex.yaml -p evals/harbor/tasks/import-two-statements --jobs-dir "$PWD/.cache/harbor/jobs"
```

Use `--model gpt-6-astra` if the default model is unavailable. No fallback model
is selected automatically. The exported `CODEX_FORCE_AUTH_JSON` opts into
`~/.codex/auth.json`; no credential values are stored in the repo. Keep this flag
in the host environment: Harbor 0.24 mistakenly treats it as a secret when placed
in `agents[].env` and then corrupts artifacts while redacting it. For API-key
authentication, unset `CODEX_FORCE_AUTH_JSON` and provide `OPENAI_API_KEY` in your
environment.

Validate both tasks without model calls:

```sh
uv run --group eval harbor run -p evals/harbor/tasks -a oracle -n 1 --jobs-dir "$PWD/.cache/harbor/jobs"
uv run --group eval harbor run -p evals/harbor/tasks -a nop -n 1 --jobs-dir "$PWD/.cache/harbor/jobs"
```

Both oracle tasks should earn 1. Both no-op tasks should earn 0, with import
approval skipped. Check task rewards and nested step errors in Harbor's results;
a zero command exit alone does not establish a workflow pass.

The custom Codex adapter appears as `auto-bean-codex` in the viewer. For older
runs, an overview link may apply an `Agent: codex` filter while the Rollouts list
uses `evals.harbor.adapter:AutoBeanCodex`. Remove that agent filter (or use
**Clear all**) to show the saved trials; their results are unaffected.

## Current plugin and fixtures

Each task's Docker Compose definition builds from this repository root. Docker
copies `plugins/auto-bean/` directly, including uncommitted edits. "Latest" means
the current local checkout, without fetching a published plugin or another Git
revision. The complete plugin is installed through a container-local marketplace.
Docker rechecks those build inputs on each run; changed plugin files invalidate
the corresponding cached layers.

CSV/PDF inputs and the independent import ledger are generated inside the images.
Regeneration overwrites previous generated fixtures. New runs create no prepared
task copies or host fixture snapshots, and require no output directory rotation.
The initialization
destination stays empty; dependency warming uses a disposable workspace elsewhere.

Harbor builds the task and separate verifier images automatically. Their shared
Dockerfile preloads runtime dependencies and PDF models, smoke-tests both raw
formats, and verifies discovery of all nine plugin skills. The first build can
take several minutes; unchanged layers are cached. Grader code and expected
answers enter only the verifier image; the reference solution is uploaded only
for oracle runs. Product skill behavior is unchanged.

## Contracts and grading

Initialization starts in an empty directory with a synthetic Git identity. It
requires the default EUR scaffold, governed memory, a working managed runtime,
one clean initial commit, no invented transactions, and no copied product skills
or tracked runtime caches.

Import supplies ownership and category decisions upfront. Checking CSV: EUR 25
food purchase, EUR 100 transfer out, EUR 5 fee. Savings PDF: EUR 100 transfer in,
EUR 2 interest. Opening balances are EUR 1,000 checking and EUR 500 savings;
closing balances must be EUR 870 and EUR 602. Five raw rows must yield four new
economic transactions, including one shared transfer with both source identities.

The review step requires both statements at `final_review` and a conversational
`Import Status: Ready For Review`. Only a full verifier pass unlocks the explicit
approval instruction, delivered by resuming the same Codex session. Approval
requires unchanged reviewed financial hashes, validation, recorded user approval,
both statements `done`, and `Import Status: Complete`. Neither import step may
stage, commit, or push. Normal EUR-only price and governed-memory outcomes must
be recorded; no new global preferences or market-price dependencies are needed.

Verifiers run separately with trusted dependencies and an immutable plugin copy.
They grade Beancount entries, Decimal amounts, accounts, provenance, balances,
schemas, and approval state. They preserve raw hashes, existing transactions,
unrelated files, and Git history. Workspace Python is never imported. Runtime
caches and temporary extractions are excluded from transferred artifacts.

Each verifier writes binary `reward.txt` and diagnostic `report.json`. Harbor
stores trajectories, timing, token usage, configuration, rewards, and transferred
ledger artifacts in `.cache/harbor/jobs/<job>/`. The transferred
`opt/eval-evidence/build.json` records the actual plugin tree hash, runtime lock
hash and dependency versions, Codex/Python versions, and cached PDF model
revisions. Runtime caches and credentials are excluded from the artifacts.
Native Codex counters are cumulative across resumed steps; use the final session
counters rather than adding review and approval usage. Inspect nested step errors
in `result.json` before interpreting a missing reward as a workflow failure.

```sh
uv run --group eval ruff check
uv run --group eval ruff format --check
uv run --group eval mypy
uv run --group eval pytest tests evals/harbor/tests
uv run --group eval python scripts/package_plugin.py --check
```

Host tests corrupt transactions, source files, provenance, status, and approval
checkpoints. They use synthetic runtime evidence; Docker control runs establish
actual runtime/extraction behavior. Historical product baseline results are in
[BASELINE.md](BASELINE.md); its frozen snapshots predate the direct task layout.

References: [task format](https://docs.harborframework.com/tasks/overview),
[multi-step tasks](https://docs.harborframework.com/tasks/multi-step),
[separate verifiers](https://docs.harborframework.com/tasks/separate-verifier),
[Codex integration](https://docs.harborframework.com/agents/pre-integrated-agents).
