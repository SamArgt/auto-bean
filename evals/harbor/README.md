# Harbor workflow evaluations

Four runnable Harbor tasks live directly in `evals/harbor/tasks/`:
`init-ledger`, `import-two-statements`, `human-input-correction`, and `stale-review`. Run commands from the repository root.
Requirements: Docker with Compose and uv; each task requests 2 CPUs, 8 GiB
memory, and 20 GiB storage. Runs are manual and use synthetic data only.

## Run

```sh
uv sync --group dev --group eval
export PYTHONPATH="$PWD"
export CODEX_FORCE_AUTH_JSON=1
uv run --group eval harbor run --config evals/harbor/codex.yaml --jobs-dir "$PWD/.cache/harbor/jobs"
```

This is Harbor's native CLI and configuration. The config runs all four tasks using
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

Validate all tasks without model calls:

```sh
uv run --group eval harbor run -p evals/harbor/tasks -a oracle -n 1 --jobs-dir "$PWD/.cache/harbor/jobs"
uv run --group eval harbor run -p evals/harbor/tasks -a nop -n 1 --jobs-dir "$PWD/.cache/harbor/jobs"
```

All oracle tasks should earn 1. All no-op tasks should earn 0, with later
steps skipped by the first-step reward gate. Check task rewards and nested step errors in Harbor's results;
a zero command exit alone does not establish a workflow pass.

The custom Codex adapter appears as `auto-bean-codex` in the viewer. For older
runs, an overview link may apply an `Agent: codex` filter while the Rollouts list
uses `evals.harbor.adapter:AutoBeanCodex`. Remove that agent filter (or use
**Clear all**) to show the saved trials; their results are unaffected.

## Current plugin and fixtures

Each task's Docker Compose definition builds from this repository root. Docker
copies `plugins/auto-bean/` and frontend sources directly, including uncommitted edits.
A pinned Node build with `npm ci` reconstructs the UI and rejects missing or stale
bundled assets by comparing the HTML and source/lock build evidence. "Latest" means
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
formats, and verifies discovery of all nine plugin skills, local MCP registration,
all expected tools, the bundled App resource, and an unbound structured call.
This does not prove desktop rendering or simulate panel button clicks. The first build can
take several minutes; unchanged layers are cached. Grader code and expected
answers enter only the verifier image; the reference solution is uploaded only
for oracle runs. Agent images contain no graders, expected answers, or oracle solutions.

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

The review step requires both statements at `final_review` with strict parsed
account mappings and transaction postings. Canonical financial files must still
match the initial baseline. The separate verifier renders the reviewed postings
in its own temporary ledger and checks the expected economics independently.
The conversation ends with `Import Status: Ready For Review`. A full verifier
pass unlocks the explicit approval instruction in the same Codex session.

The explicit approval turn authorizes direct canonical ledger writes,
independent transaction coverage and closing-balance validation, both statements
`done`, and `Import Status: Complete`. Written validation must describe the current parsed decisions and canonical
ledger; a review-stage report cannot certify completed writes. The verifier compares current material
review digests with the preserved checkpoint and independently checks actual
ledger economics and provenance. Neither step may commit or push. The normal
EUR-only price result must be recorded. Eligible account and merchant decisions
are saved in governed memory only after approved, validated writes. Their audit
retains source, review digest and validation provenance. `MEMORY.md` remains
unchanged because no global preferences were requested.

The correction task first requires unresolved inline mapping/category suggestions.
A later user turn supplies answers, which update those fields; a separate turn
supplies approval. The `stale-review` task makes a harness-controlled change to a
reviewed transaction rationale and then authorizes only the earlier review. The
agent must preserve the changed decision, refuse the stale digest and present
renewed review without ledger writes. These headless tasks use conversation
submissions; MCP/browser integration tests exercise panel controls.

The session contains statement membership and price runs. Parsed statements
contain source facts, inline account/transaction decisions and generated
validation results. Agents edit these documents and status YAML directly; the
reference uses only the public validation operation after writing. Chat approval
is established by the harness step and immutable checkpoint, never by an
agent-authored approval field. Panel receipts are not expected in headless tasks. There are no session write targets, candidates or
action histories. The host checkpoint captures the reviewed parsed documents,
material digests and canonical baseline; the verifier derives expectations from
those documents rather than trusting submitted execution claims. Static HTML
artifacts render that same lightweight review. Historical baseline runs retain
their original contract and are not credited to this changed contract.

The adapter reads each native step setup marker before agent execution. It never
infers approval from session resumption. It downloads the review checkpoint into
trial-level `review-checkpoints/` outside the agent workspace, refuses overwrite,
and explicitly restores that copy for later separate-verifier artifact transfer.

Verifiers run separately with trusted dependencies and an immutable plugin copy.
They grade Beancount entries, Decimal amounts, accounts, provenance, balances,
schemas, validation stage, and the authorized phase. They preserve raw hashes, existing transactions,
unrelated files, and Git history. Workspace Python is never imported. Runtime
caches and temporary extractions are excluded from transferred artifacts.

Each verifier writes binary `reward.txt` and diagnostic `report.json`. Harbor
stores trajectories, timing, token usage, configuration, rewards, and transferred
ledger artifacts in `.cache/harbor/jobs/<job>/`. The transferred
`opt/eval-evidence/build.json` records the actual plugin tree hash, runtime lock
hash and dependency versions (including MCP), supported schema versions, frontend
source/bundle/lock identity, Codex/Python versions, and cached PDF model
revisions. Runtime caches and credentials are excluded from the artifacts.
Each import phase also captures a self-contained, read-only `review.html` under
`opt/eval-evidence/`; the Codex adapter downloads a host copy to
`review-exports/<phase>.html`. The separate verifier renders a second copy from
its transferred artifacts into the step's `verifier/review.html`, including a
clearly labelled unavailable report for no-op or invalid runs. Initialization
has no import review export. These HTML files are derived inspection artifacts;
they never replace the strict JSON, approval checkpoint, or independent financial
checks, and opening them does not submit decisions or approve changes.

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

Host tests corrupt structured proposals, source identities, transfer ownership,
inline decision and answer references, price results, actual governed-memory
records and provenance, premature writes/learning, and approval checkpoints.
They exercise correction and stale-baseline sequences and native step identity. They use synthetic runtime evidence; Docker control runs establish
actual runtime/extraction behavior. Historical product baseline results are in
[BASELINE.md](BASELINE.md); its frozen snapshots predate the direct task layout.

References: [task format](https://docs.harborframework.com/tasks/overview),
[multi-step tasks](https://docs.harborframework.com/tasks/multi-step),
[separate verifiers](https://docs.harborframework.com/tasks/separate-verifier),
[Codex integration](https://docs.harborframework.com/agents/pre-integrated-agents).

## Evaluation execution policy

Run Harbor, including Docker oracle/no-op controls, only when explicitly requested.
Local verifier/adapter unit tests can run with product checks. The lightweight
direct-write review contract is a breaking evaluation change; a fresh Harbor run
should be suggested separately, never started automatically.
