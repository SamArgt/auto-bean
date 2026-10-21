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
