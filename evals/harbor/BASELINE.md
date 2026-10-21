# Direct Harbor validation - 2026-10-21

The current task directories run directly through Harbor. The old prepare/build
runner has been removed. Native CLI checks on the current layout:

| Agent | Initialize ledger | Import two statements |
| --- | --- | --- |
| Oracle | 1 | 1; review and approval both pass |
| No-op | 0 | 0; approval skipped |
| Codex / GPT-6.1-Sol | 1 | Not rerun after the layout change |

The native Codex initialization used the existing sign-in, initialized the EUR
ledger, validated it, and made one clean local commit without invented balances
or transactions. All saved JSON files in the clean trial parse successfully.
The image's plugin tree hash matches the current checkout, including uncommitted
plugin files:
`d8db0403dea7b6690d1fe3361f3b4c0a9301e9aea13d3787f604db739fef16f2`.
Its build metadata records Codex 0.163.0, Python 3.13.12, locked runtime dependency
versions, the runtime lock hash, and PDF model revisions.

The import's successful real Codex baseline below predates this layout change.
The current native oracle separately passed both import steps with the same
financial and approval assertions. Product skill behavior was not changed.

Evidence:

- Native oracle: `.cache/harbor/direct-jobs/2026-10-21__11-01-21/`.
- Native no-op: `.cache/harbor/direct-jobs/direct-noop/`.
- Clean native Codex initialization: `.cache/harbor/direct-jobs/direct-codex-init-clean/`.

Repository checks: uv sync, 89 tests, Ruff check/format, Mypy, plugin package
validation, and `git diff --check` pass. Tests also cover fixture overwriting,
current plugin hash changes, direct task/config parsing, shared oracle fallback,
and keeping graders out of agent images.

The first native build probe missed the bundled verifier entrypoint; the image
now copies the task's `test.sh` explicitly. An initial Codex probe exposed a
Harbor 0.24 redaction bug: putting `CODEX_FORCE_AUTH_JSON=1` in `agents[].env`
causes every digit 1 in trial files to be replaced as a secret. That corrupted
probe (`direct-codex-init/`) is superseded by the clean trial. The documented
native commands keep this flag in the host environment and use absolute result
paths to avoid Compose path-resolution issues.

The older snapshot directories below are retained historical evidence and are
not inputs to the current tasks.

---

## Original frozen baseline - 2026-10-21

Environment: local Docker with Linux ARM64 containers, Harbor 0.24.0, Codex
0.163.0, `gpt-6.1-sol`, and the existing Codex sign-in. The runner defaults to
this model; `--model gpt-6-astra` is available as the authorized availability
fallback. The successful runs did not need that fallback.

| Agent | Initialize ledger | Import two statements |
| --- | --- | --- |
| Oracle | 1 | 1; review and approval both pass |
| No-op | 0 | 0; approval is skipped |
| Codex / GPT-6.1-Sol | 1 | 1; review and approval both pass |

Initialization's actual conversation reports successful validation, a clean
initial commit, no invented transactions/opening balances, and the installed
plugin's import/query/write/Fava routes. The independent verifier confirmed the
financial scaffold and runtime checks.

The import trajectory processed both raw formats with Docling, reconciled all
five source records into four economic transactions, and retained both source
identities on one transfer. Review left both statements at `final_review`.
Harbor resumed native Codex session `01a15d8c-bc77-7bb1-99b0-64b124327ed7`
for approval; both steps report that same session ID. Before acceptance, Codex
checked all three financial candidate hashes, both raw fingerprints, and fresh
ledger/schema validation. Both statements then became `done`, and the final
response ended with `Import Status: Complete`.

Closing balances were EUR 870 checking and EUR 602 savings. Price processing
recorded a EUR-only `no_op`; governed memory retained the five supplied mapping
decisions. Proposed document directives were excluded from the exact approved
transaction candidate. No transactions were appended again, financial candidates
remained unchanged, and no files were staged, committed, or pushed. Source files,
existing transactions, unrelated files, and Git history were preserved.

| Successful live trial | Agent execution | Input tokens | Cached input tokens | Output tokens |
| --- | ---: | ---: | ---: | ---: |
| Initialize | 44.2 seconds | 82,063 | 76,544 | 493 |
| Import, review plus approval | 438.5 seconds | 1,721,241 | 1,630,464 | 11,952 |

These are native Codex usage counters. Input includes cached input. The resumed
session's counters are cumulative: use its final counters, not the sum of review
and approval counters. Harbor's raw per-step metrics and timestamps remain in
the results; cost estimates there are not billing evidence.

Validation: uv dependency sync, 89 tests, Ruff check/format, Mypy, plugin package
validation, and `git diff --check` pass. Both source formats were processed by
actual Docling during container preparation; the synthetic PDF was also
rendered and inspected.

Frozen plugin revision: `ec8cfe248f66abfdf4115e2bde157defc1f57855`.
Plugin bundle SHA-256:
`e262eb9ffd97a4f1273db9f300f4ad6584ed3df6a7f43f2e0ad6cb80c5fd46ed`.
Final suite SHA-256:
`b7f0cdbf3bcd83eed73714ddf67498270f80c518be756ac2364253262eec00e6`.
The bundle includes the checkout's concurrent import-flow documentation changes;
this evaluation work did not edit product skills.

Local generated evidence (gitignored):

- Final snapshot and image/model revisions: `.cache/harbor-finalized/manifest.json`.
- Final oracle job: `.cache/harbor-finalized/jobs/2026-10-21__10-19-06/`.
- Final no-op job: `.cache/harbor-finalized/jobs/2026-10-21__10-20-37/`.
- Successful live import: `.cache/harbor-finalized/jobs/2026-10-21__10-21-04/`.
- Successful live initialization: `.cache/harbor-release/jobs/2026-10-21__09-54-52/`.

Earlier development evidence remains available. The first real import in the
initialization job stopped with `ApiOverloadedError` (model at capacity), so it
has no workflow score. Two subsequent development imports exposed verifier
defects: transaction-only provenance inspection rejected valid posting metadata,
and a literal-filename check rejected clear "Checking CSV" / "Savings PDF"
labels. Those grades are superseded. Both checks were corrected against the
existing product contract with regression tests; transaction counts, amounts,
categories, balances, provenance, approval, and preservation expectations were
unchanged. Both controls were rerun on the final frozen suite before its live
import passed.

Earlier compatibility probes used Codex 0.149.1, which rejected GPT-6.1-Sol with
the sign-in. Pinning the container to 0.163.0 resolved model access.

## 2026-10-21: structured review and local panel workflow

Review semantics changed. Canonical financial files now remain at their original
baseline throughout review. The trusted verifier reconstructs staged candidates
in temporary storage and checks five source rows, four economic transactions,
one transfer with both source identities, and EUR 870 / EUR 602 closing balances.
The resumed approval step must apply the exact reviewed candidate once. These
scores and timings are not directly comparable with the preceding Markdown-based
review baseline, which expected transactions already in canonical files.

The suite now includes explicit human-input correction and stale-candidate tasks.
Their headless submissions use later user turns; they do not simulate panel
button clicks. Actual desktop acceptance is recorded separately in
[the implementation evidence](../../docs/import-review-implementation.md).

| Control | Initialization | Two statements | Human correction | Stale candidate |
| --- | --- | --- | --- | --- |
| Oracle | 1 | review 1, approve 1 | needs-input 1, correct 1, approve 1 | review 1, stale 1 |
| No-op | 0 | review 0; approval skipped | needs-input 0; later steps skipped | review 0; stale step skipped |

The final no-op job completed all four trials without infrastructure exceptions.
The three import oracle tasks passed in `review-ui-oracle-complete`. Its init
trial exposed an oracle wrapper still using the removed capture phase `initial`:
initialization succeeded, but runtime evidence was missing. The wrapper now uses
`init`; the focused `review-ui-oracle-init` rerun passed all unchanged financial
and scaffold assertions. The combined job's historical mean remains 0.75; the
focused successful rerun is recorded separately rather than rewriting that job.

Earlier build/probe attempts exposed and fixed three integration defects: Linux
stdio startup selected the wrong Python prefix with a relative argv[0]; the
probe's default 64 KiB line buffer could not read the bundled HTML resource; and
oracle scripts lost the trusted `/opt` helper path when the launcher set its
plugin import path. These were real failures, retained in local job evidence.
The product launcher now uses its absolute environment interpreter; the probe
accepts an 8 MiB resource line; oracle wrappers explicitly import trusted image
helpers. No financial expectations were relaxed.

Candidate validation also now requires the displayed patch to match the exact
baseline and target content. Both product runtime and independent verifier
reject a misleading patch even when candidate hashes are recomputed. The initial
live evaluation was stopped before grading, then controls were rerun with the
guard in the current package. The guarded oracle run passed initialization,
two-statement review/approval, and all three correction steps before its host
process was interrupted during preparation of the final stale task. Its result
file remains incomplete. The focused `review-ui-oracle-stale-final` run passed
review and stale refusal (1/1) without exceptions in 2m 47s. All guarded
control task expectations have therefore passed; this does not rewrite the
interrupted combined job as complete.

Host validation: 58 Harbor tests pass, including independent reconstruction,
canonical-write and candidate tampering failures, source/reference corruption,
missing price/memory outcomes, replayed approval, interrupted application,
correction and stale-baseline sequences, native step identity, and rejection of
executable directives in recursively included nonstandard file suffixes. Scoped
Ruff, formatting, Mypy and `git diff --check` pass. Docker discovery checks all
nine installed skills, MCP registration/tools, the App resource and an unbound
structured call; resource retrieval is not evidence of desktop rendering.

The tested image contains current uncommitted checkout changes. Build evidence:

- Plugin tree SHA-256: `e1bf8a8340698c7b657efd61897b2a2e44272bd60bd423c5adb09968f361da20`.
- Runtime lock SHA-256: `12ef19c1904183314858b53338bb1ac1e085c0179a899a3453ed68f0d1b2b642`.
- Frontend bundle SHA-256: `bf91f06018bcd2ea751b14ac1414ef6a2f1d15e4fd94e7a02b15e20bd13f3198`.
- Full frontend source/lock identity, runtime dependency versions (including MCP),
  schema versions and cached PDF model revisions are in each transferred
  `opt/eval-evidence/build.json`.

Local evidence, all under `.cache/harbor/review-ui-jobs/`:

- Import oracle controls: `review-ui-oracle-complete/`.
- Corrected initialization oracle: `review-ui-oracle-init/`.
- Guarded oracle controls: `review-ui-oracle-guarded/` (three completed tasks pass; interrupted during the fourth), plus `review-ui-oracle-stale-final/` (review 1, stale 1).
- Final guarded no-op controls: `review-ui-noop-guarded/` (4/4 reward 0, zero exceptions; 10m 52s including image builds).
- Initial pinned Codex evaluation: `review-ui-codex/` (deliberately canceled before grading after a displayed-patch consistency gap was discovered; no completed workflow score).

The pinned four-task live run `review-ui-codex-final/` completed in 20m 50s
with zero infrastructure exceptions. Its recorded mean remains 0.50:

| Live task | Recorded steps | Interpretation |
| --- | --- | --- |
| Initialization | 1 | Complete scaffold/runtime pass |
| Two statements | review 1, approve 1 | Exact candidate applied once; balances and preservation pass |
| Human correction | needs-input 1, correct 0; approval skipped | Verifier rejected valid transfer delegation |
| Stale candidate | review 1, stale 0 | Verifier rejected refreshed query provenance |

The correction's non-owner transfer record references its owner and shared
candidate instead of repeating the owner's postings. The verifier now resolves
that relationship and requires reciprocal source links, exact owner postings,
and the one shared candidate. Empty or incorrect owner postings, bad links and
missing candidate references still fail. The stale agent preserved the baseline
edit, refused the prior approval, and prepared fresh unapproved review; only
reconciliation provenance gained updated query timestamps and candidate labels.
The stale preservation comparison now excludes only that attribution text.
Amounts, dates, mappings, source facts and postings must remain unchanged, and
the fresh candidate still binds the complete material digest, including its
updated provenance. Thirteen positive/negative host regressions cover both fixes.

An independently regenerated host fixture exactly matches the Docker fixture's
starting Git HEAD and raw hashes. Regrading the captured six import/correction/
stale steps with the corrected verifier passes all six; those diagnostic results
are in `.cache/harbor/regrade-fixture/transfer-regrade.json`. Original Harbor
results are not rewritten. Focused native correction/stale controls completed:
oracle 1/1/1 and 1/1 in 4m 55s; no-op 0 and 0 in 1m 16s, with later steps
gated. Both jobs had zero exceptions. Their evidence is in
`review-ui-oracle-semantics-final/` and `review-ui-nop-semantics-final/`.

| First live run | Agent execution | Final input tokens | Cached input tokens | Output tokens | Harbor estimated USD |
| --- | ---: | ---: | ---: | ---: | ---: |
| Initialize | 36.2 s | 100,106 | 89,472 | 600 | 0.0362 |
| Two statements | 434.8 s | 2,333,727 | 2,260,224 | 14,897 | 0.5220 |
| Human correction (approval gated) | 264.0 s | 1,022,369 | 935,168 | 8,563 | 0.3535 |
| Stale candidate | 236.5 s | 1,546,016 | 1,462,784 | 9,382 | 0.4066 |

The live package includes the final empty-account-filter UI correction. Its plugin
tree SHA-256 is
`1157b8117dd7eb2038d9b751cd8bd335329863ed87a54964f7b6baf70e3a9b83`
and frontend bundle SHA-256 is
`83e33149527f21f13ba9346eb7827c910ac1ceea87502880ee8640333e87750e`.
Product contents remain unchanged for the focused reruns; only the verifier is
corrected (SHA-256 `ae710097b425a4af699e6bed1a8a7aa13f60bc949da43f77e5c624806c26f74d`).
No complete native correction result is inferred from regrading.

The focused live run `review-ui-codex-semantics-final/` completed at 14:03 CEST
on 2026-10-21 in 15m 30s with zero exceptions. Correction passed all three native
steps (needs-input 1, correct 1, approve 1); stale-candidate passed review 1 and
stale refusal 1. Together with the unchanged initialization and two-statement
successes above, every task now has a complete native live pass under the
corrected grading semantics. The earlier combined job remains recorded as 0.50.
The first focused launch rejected a CLI filter without an explicit dataset path;
no model call occurred. That launch log is retained beside the successful job.

| Successful focused live task | Agent execution | Final native input tokens | Cached input tokens | Output tokens | Harbor estimated USD |
| --- | ---: | ---: | ---: | ---: | ---: |
| Human correction | 396.2 s | 1,730,910 | 1,656,960 | 11,606 | 0.4297 |
| Stale candidate | 332.8 s | 1,846,054 | 1,762,176 | 8,873 | unavailable reliably |

The focused stale result's Harbor `agent_result` repeats a smaller token counter
for both steps and disagrees with its root `codex.txt` final `turn.completed`
event. The table uses that native cumulative event, as required. Its Harbor cost
estimate is therefore omitted rather than presented as comparable usage.
These runs precede the subsequent read-only static HTML export addition;
financial implementation and approval behavior were frozen through both runs.
HTML artifact integration is validated separately below, without attributing it
to a live package that did not yet contain it.

Live usage must use the final cumulative session counters for each task, not the
sum of resumed-step counters. Token-based cost estimates are not billing data.

### Static HTML artifact addition

After the financial live runs completed, the package gained a read-only HTML
export of the selected session review. Each import phase saves
`opt/eval-evidence/review.html`; the Codex adapter explicitly downloads
`review-exports/<phase>.html` outside the agent workspace. The separate verifier
renders its transferred state into `verifier/review.html`, including a clearly
labelled unavailable document when no valid session exists. Initialization is
excluded. These derived documents cannot approve or mutate the ledger and do
not replace strict JSON or independent reconstruction.

The export includes all source-row review data, questions, candidate diffs and
approval/application history. Raw statement binaries and reconstruction-only
whole-file candidate contents are excluded. The latter prevents an export from
copying unrelated ledger history beyond the displayed patch context. Rendering
escapes user data and makes no external asset or telemetry requests.

Host validation now includes 68 Harbor tests. Export coverage includes trusted
isolated plugin imports, unavailable/error documents with escaped content, every
import phase, initialization exclusion, explicit host downloads, and exact
agreement between the packaged tools and the discovery probe. Read-only
examples generated from copies of the successful two-statement live artifacts
are in `.cache/harbor/static-reviews/two-statements-{review,approve}.html`.
The historical agent artifacts were not modified.

Final artifact package identity:

- Plugin tree: `095a51e4e6d765b6fea01be3b2999ec36da46ccb00456c9ba768d3de7a7e99bb`.
- Frontend bundle: `39be0c3e87b54e6736833c450911950325119e82b96c778c77c7b8c6c4371c5e`.
- Verifier: `9a8dcf1ff31752d6f8297e6d3195cb1ca94b9b0a159c56b9955098a8a949dfc9`.

The first focused HTML controls, `review-ui-oracle-html-final/` and
`review-ui-nop-html-final/`, failed during image discovery: the probe's exact
expected-tool set had not included the new `export_import_review` operation.
Both jobs recorded two infrastructure exceptions before workflow execution.
Their original results and build logs are retained. The probe is corrected and
a host regression now compares its complete expected set against the actual
packaged tool inventory.

Corrected controls completed on 2026-10-21 as
`review-ui-oracle-html-probe-final/` (5m 24s) and
`review-ui-nop-html-probe-final/` (2m 27s), both with zero exceptions. The oracle
passed correction 1/1/1 and stale-candidate 1/1. Every one of the five phases
(`needs-input`, `correct`, `approve`, `review`, `stale`) retained a nonfallback
HTML review in both its transferred `artifacts/opt/eval-evidence/review.html`
and trusted `verifier/review.html`. Each contains both selected statements.
No-op scored 0 for both tasks, gated all later steps, and retained explicit
unavailable HTML in each executed step's verifier artifacts.

The independent file audit at
`.cache/harbor/review-ui-jobs/review-ui-html-artifact-audit.json` records the
seven verifier HTML paths, byte counts, SHA-256 hashes and unavailable flags.
These controls verify real Harbor artifact retention; the Codex adapter's
additional `review-exports/<phase>.html` download path is covered by host tests.
This read-only artifact change did not trigger another paid financial live run.

## Inline parsed review contract (2026-10-21)

The current checkout simplifies the unreleased parsed-v2 contract: account
mapping decisions live on each extracted account, and posting decisions live on
each extracted record. Required input uses inline `state: needs_input`,
`suggestions`, and an optional `answer`; statement extraction input lives under
`review.processing`. Exact candidate patches, ownership, approvals, and recovery
remain shared document/cohort records. The prior controls and live scores above
used the earlier document-level decision/question maps and are historical
evidence, not passes for this revised contract.

The verifier now reads inline decisions independently and computes the exact
revised material digest without importing executable code from the submitted
ledger workspace. It retains the five source rows, four economic transactions,
shared transfer, EUR 870/EUR 602 closing balances, baseline immutability, and
approval checkpoint checks. Human-input evaluation accepts a consumed typed
answer or an explicit mapping/posting correction; an answer by itself does not
resolve `needs_input` or approve a candidate. Oracle/reference fixtures and the
correction instruction use this same contract. Checkpoint capture still retains
full parsed documents and candidate identities; HTML capture uses the updated
renderer without creating another authoritative state file.

Host validation on this checkout: **76 Harbor tests passed** (9.53s); scoped Ruff
checks/formatting and Mypy over all 13 Harbor Python files passed. Added cases
cover account/transaction/statement input gates, typed answer target mismatches,
correction without a redundant answer, omitted optional empty transaction lists,
and independent material-digest parity. These are host tests, including the
reference workflow; Docker oracle/no-op controls and paid live Codex evaluations
have not yet been rerun for this contract.

The initial Docker attempt `inline-review-oracle-20261021/` was intentionally
interrupted during its first image build when code review found a reparse
source-identity bug. It exited 130 with one cancellation, zero scored trials,
and two pending tasks. Its logs and partial result remain preserved, together
with `INTERRUPTED-PRE-FIX.md`; no no-op control was started for that snapshot.
This interrupted attempt provides no validation result for the revised contract.

Post-fix Docker controls completed on 2026-10-21 against the frozen checkout:

| Control | Standard import | Human correction | Stale candidate | Elapsed | Exceptions |
| --- | --- | --- | --- | --- | --- |
| `inline-review-oracle-postfix-20261021` | 1 / 1 | 1 / 1 / 1 | 1 / 1 | 9m 30s | 0 |
| `inline-review-nop-postfix-20261021` | 0; approval gated | 0; correction/approval gated | 0; stale step gated | 1m 40s | 0 |

Both commands exited zero. The oracle completed all seven phases; no-op executed
only the first phase of each task, with zero rewards and no later step results.
No paid live Codex evaluation was run for this revision. Commands from the repo
root (with `PYTHONPATH=$PWD` and a writable `UV_CACHE_DIR`):

```sh
uv run --group eval harbor run -p evals/harbor/tasks -i '*import-two-statements' -i '*human-input-correction' -i '*stale-candidate' -a oracle -n 1 --jobs-dir "$PWD/.cache/harbor/review-ui-jobs" --job-name inline-review-oracle-postfix-20261021
uv run --group eval harbor run -p evals/harbor/tasks -i '*import-two-statements' -i '*human-input-correction' -i '*stale-candidate' -a nop -n 1 --jobs-dir "$PWD/.cache/harbor/review-ui-jobs" --job-name inline-review-nop-postfix-20261021
```

Captured build identity matches the frozen host audit:

- Plugin tree: `883f06db1e686f4e4f354ed4c06791c105186bab2be47a6eab960a36dd9c2d87`.
- Frontend bundle: `58cc6a22b6a96689157148223087ba7779d67042b2657c836cbd1c0faa28d030`.
- Parsed-v2 schema: `a5d930c46e21d8df2b443c2c9d85e8e004ea10ecc6342a506969c6553f8bb494`.
- Verifier: `9e6ff269cc5dffcb9c104c5d6fa137d4e44f6b792d2afd2b5f8c822f34946959`.

The independent artifact audit is
`.cache/harbor/review-ui-jobs/inline-review-postfix-artifact-audit-20261021.json`.
It records hashes and byte counts for all fourteen oracle HTML copies (seven
transferred and seven trusted verifier exports), plus the three no-op verifier
unavailable exports. Each oracle HTML embeds readable snapshot JSON matching its
transferred statement documents, except the exporter's intentional omission of
full candidate target file contents; exact patches and hashes remain present.
Every phase retains two extracted accounts and five source records with inline
reviews and no document-level account, transaction, or question maps. The first
correction phase includes its mapping and category suggestions. No-op has no
agent-produced export because it performs no capture; its verifier still emits
an explicit unavailable HTML artifact. All captured build records match the
frozen plugin and bundle identities above. This checks real Harbor artifact
retention and financial invariants, not desktop button interaction.

## Session change simplification (2026-10-21)

Parsed statements no longer store candidates or candidate references. One
`session.changes` list contains exact pending writes and their statement membership.
Each change references its explicit approval action in `session.actions`; baseline
hashes remain once per change, and result hashes are derived from exact target
contents. The frozen review checkpoint captures this session list. The independent
verifier still reconstructs the proposed ledger, verifies the displayed patches,
preserves the before-approval baseline check, and compares the applied result with
the previously reviewed contents.

The adapted Harbor host suite passed **79 tests in 9.48 seconds**, including the
standard review/approval oracle, human correction, stale refusal/renewal, no-op
failure checks, frozen-checkpoint tampering, transfer membership/duplication and
three new exact approval-action binding checks. Ruff, formatting, Mypy and scoped
diff checks passed. The older missing/incorrect candidate-reference defects now
exercise missing session membership and duplicate shared changes. No test accepts
prose as financial or approval evidence.

These are host tests exercising the reference workflow with synthetic evidence.
Docker controls and paid live evaluations above remain evidence for their earlier
builds; they have not been rerun for this contract revision.

Fresh Docker controls for the standard two-statement task subsequently passed:

| Control | Review | Approval | Elapsed | Exceptions |
| --- | --- | --- | --- | --- |
| `session-changes-oracle-20261021` | 1 | 1 | 5m 1s | 0 |
| `session-changes-nop-20261021` | 0 | Gated | 1m 26s | 0 |

Both commands exited zero. The initial oracle image rebuilt from the uncommitted
checkout, reproduced the bundled frontend, ran real CSV/PDF extraction and passed
plugin/MCP discovery including `read_import_change`. Run commands, with a writable
uv cache and the repo root on `PYTHONPATH`:

```sh
uv run --group eval harbor run -p evals/harbor/tasks/import-two-statements -a oracle -n 1 --jobs-dir "$PWD/.cache/harbor/review-ui-jobs" --job-name session-changes-oracle-20261021
uv run --group eval harbor run -p evals/harbor/tasks/import-two-statements -a nop -n 1 --jobs-dir "$PWD/.cache/harbor/review-ui-jobs" --job-name session-changes-nop-20261021
```

The oracle captured plugin tree
`dd362bf22c1f9f3a3d8937cc1bc4fc350509100292024c441d25f95b0669bba6`,
frontend bundle
`478d8d77f85207befe8ddf00c51657ad01cddf74254ca4d9c47b790aecd88fb3`,
and verifier
`2db4573057ef362b7d9c6b8163f9d714def3ce4d4ba21825f4dd27294484da38`.
The no-op captured the same frontend but later reference-example edits, giving
plugin tree
`fd41c9b2122876906d35ee24de37a86082888b862c5b58f326f18c40ad81f438`.
Runtime/frontend code remained unchanged while the examples were expanded; these
results do not claim that both complete plugin trees are identical or validate
later example content merely through the oracle run.

The artifact audit at
`.cache/harbor/review-ui-jobs/session-changes-artifact-audit-20261021.json`
records all four oracle HTML files (transferred and separate-verifier copies),
their hashes and sizes, plus the no-op unavailable-review HTML. Each oracle HTML
contains exactly one shared change section, matches the transferred parsed/session
data with reconstruction-only target contents omitted, and preserves all five
source rows. Parsed documents have no candidates or candidate references. The same
change digest advances from staged to applied; its approval action ID resolves to
the consumed session action with the exact subject and digest. The frozen build
hashes are retained in `session-changes-build-audit-20261021.json` alongside the
artifact audit. No paid live evaluation or additional Docker scenario was run.

## Governed-memory evidence without import markers (2026-10-21)

The parsed review memory block is removed with no session replacement. Import
evaluation now checks actual `.auto-bean/memory/account_mappings.json` and
`category_mappings.json` records after approved application. Required reusable
decisions are independently grounded in the fixture's two external account
identities and Example Market transaction. The approval instruction asks the
agent to derive eligible memory from accepted decisions, without supplying the
expected mappings as a grading shortcut.

The verifier checks stable record IDs, accepted review state, narrow
account/owner/currency scope, exact source path/fingerprint and audit links to the
session, applied change digest and consumed approval action. Creation timestamps
must follow application. Decision memory remains empty during review, unresolved
input and stale-approval refusal. The fixture preserves `MEMORY.md` because no
global preference update was authorized. Source-format observations remain
separate from learned accounting decisions. No completion/no-op marker substitutes
for saved eligible records.

The oracle writes real records only after application and preserves record IDs,
creation timestamps and audit context on replay. Host tests passed **88 tests in
11.08 seconds**, including missing, conflicting, duplicate, provisional,
premature, overly broad and incorrectly attributed memory records. Ruff,
formatting, Mypy and scoped diff checks passed. The standard/correction/stale
reference workflows and no-op rejection run in these host tests; the preceding
Docker and live results retain their earlier memory contract and are not evidence
for this later revision.

Fresh Docker controls for this memory contract completed against one frozen
checkout:

| Control | Review | Approval | Elapsed | Exceptions |
| --- | --- | --- | --- | --- |
| `governed-memory-oracle-20261021` | 1 | 1 | 5m 20s | 0 |
| `governed-memory-nop-20261021` | 0 | Gated | 41s | 0 |

Both commands exited zero. The oracle rebuild reproduced the frontend bundle and
passed actual CSV/PDF extraction and local plugin/MCP discovery. Run commands from
the repo root with `PYTHONPATH=$PWD` and a writable `UV_CACHE_DIR`:

```sh
uv run --group eval harbor run -p evals/harbor/tasks/import-two-statements -a oracle -n 1 --jobs-dir "$PWD/.cache/harbor/review-ui-jobs" --job-name governed-memory-oracle-20261021
uv run --group eval harbor run -p evals/harbor/tasks/import-two-statements -a nop -n 1 --jobs-dir "$PWD/.cache/harbor/review-ui-jobs" --job-name governed-memory-nop-20261021
```

Both runs captured plugin tree
`e9928a0d2376d9907b424f062417c94331fe436d7cf0644892a0bbcdb7ce6da3`
and frontend bundle
`ffa8c96da2464da9f80cd281720eed3d8f54672482b06def9ececc37b502257b`.
The frozen verifier SHA-256 is
`5728ae7ed4a8e726da3ed169b2f61786518605abc39022c096ac7095457c308c`.
Full build identity is saved in
`.cache/harbor/review-ui-jobs/governed-memory-build-audit-20261021.json`.

The actual artifact transfer retained empty account/category files at review and
two account records plus one merchant-category record after approval. Each saved
record retains a stable ID, matches the transferred source fingerprint, names the
same applied change digest and consumed approval action, and is created after
application. `MEMORY.md` remains byte-identical across phases. The separate
verifier's approval score includes its checks of these transferred governed files,
not a memory completion claim.

The audit at
`.cache/harbor/review-ui-jobs/governed-memory-artifact-audit-20261021.json`
records memory-file hashes/IDs and all four oracle HTML copies. Each HTML matches
the transferred session/parsed data, contains one shared change section and has no
parsed or session memory block. The no-op retains empty memory and an explicit
unavailable-review HTML artifact. Approval is gated after its zero review reward.
No additional Docker scenario, desktop installation or paid live evaluation was
run for this revision.

## Lightweight parsed review and direct writes (2026-10-21)

This revision removes session write candidates and action history. Review captures
the parsed transaction decisions and their material digests. Approval authorizes
direct ledger writes; the separate verifier independently reconstructs reviewed
economics and checks actual provenance, row coverage, final balances and current
validation. The stale task is now `stale-review`, which changes reviewed decision
evidence rather than a stored write baseline.

This is a breaking evaluation-contract change. No Harbor CLI, Docker oracle/no-op
control or paid live evaluation was run for this revision, as requested. Earlier
results above remain historical evidence for their original contracts. Local
verifier and adapter checks passed **77 tests in 8.44 seconds**; scoped Ruff
checking/formatting, Mypy (13 source files) and diff checks passed. These are
unit/integration tests on local synthetic fixtures, not Harbor task executions.

## Direct artifact editing and one validation operation (2026-10-21)

Agent-facing persistence APIs and document revisions are removed. Reference
solutions now edit parsed JSON, session JSON and status YAML directly and write
reviewed transactions into the canonical ledger. Their only runtime operation is
import validation. Chat approval comes from the explicit harness step and the
immutable preceding review checkpoint; these headless fixtures do not fabricate
panel approval receipts. The verifier requires current `written` validation for
completion and accepts `review` validation only as a pre-write check. Financial
reconstruction, exact source coverage, transfer ownership, final balances and
memory provenance remain independent assertions. Import artifacts continue to
include the self-contained static review HTML.

This changes the evaluation contract. No Harbor CLI, Docker build, oracle/no-op
job or live Codex evaluation was run. Historical results above describe their
original contracts. Local host verifier/adapter tests passed **82 tests in 7.81
seconds**, including direct-edit checkpoint conflicts, fabricated panel receipts,
review-versus-written validation, and removed revision fields. Scoped Ruff,
Mypy (13 source files) and diff checks passed. These checks use local synthetic
fixtures; they are not Harbor executions.
