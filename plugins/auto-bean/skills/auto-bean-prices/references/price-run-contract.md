# Price Run And Artifact Contract

Apply this contract to every Beanprice fetch.

## Fetch modes

- `snapshot`: Use for import epilogues and normal updates. Choose one explicit target date and run `auto_bean bean-price --date <target-date> ledger.beancount` without `--update`.
- `historical_backfill`: Use only when the user explicitly requests historical coverage. Dry-run the exact `--update` command first and record its target date range and job count before executing it live.

Before every live fetch, including snapshots and exact-source probes, run the same command with `--dry-run` and record its terminal result and listed job count. Keep the date, sources, and selection flags identical for the live command; stop if preflight fails. For a snapshot, use `auto_bean bean-price --dry-run --date <target-date> ledger.beancount`, then remove `--dry-run` and add `-v` for the live fetch. For a probe, apply the same sequence to `-e '<QUOTE>:<SOURCE>/<SYMBOL>'` with an explicit target date. Count listed jobs, not stderr log lines.

Use Beanprice's default worker count unless the user explicitly requests a concurrency change.

## Completion and reconciliation

Use a 180-second execution budget for each fetch, separate from runtime preparation. On timeout, terminate the same process/session, collect its terminal result, and mark the run failed; do not start competing retries. Retry only a clearly transient failure once after the original has terminated.

Run the live command with verbose logging so redundant directives and provider failures are observable. If the command returns a running session identifier, poll the same session until it exits. A running session, an initial empty chunk, or partial stdout is not a completed command.

Classify the run only after receiving its terminal exit code:

- `succeeded`: exit code is zero, no provider error is present, and every dry-run job is accounted for by an emitted directive or an explicitly logged redundant directive.
- `no_op`: exit code is zero and either the dry run contained no jobs or every job was explicitly logged as redundant.
- `failed`: exit code is nonzero, stderr contains a provider error, or one or more dry-run jobs remain unaccounted for.

Zero emitted directives alone is not success or failure. It is a valid `no_op` only when the reconciliation above accounts for every job. Do not draft fallback directives or run narrower probes while the original command is unresolved, and never describe an unresolved run as completed.

## Price artifact

Create `.auto-bean/artifacts/prices/<run-id>--prices.md` before fetching and update that same artifact on resume. Import links it from the affected statement artifacts. Record required commodities separately from jobs: a zero-job run does not mean all held commodities have source coverage. Treat any required commodity without a source as an explicit skipped/blocking follow-up. Before returning record: Record:

- fetch mode and target date or historical date range
- dry-run job count
- terminal completion state and exit code
- start time, end time, and duration
- emitted directive count and redundant/ignored count
- sanitized stderr summary, including provider warnings or errors
- reconciled job count and any unaccounted jobs
- changed price files or explicit skipped mutation
- provider quote dates versus requested dates, source coverage, stale/mismatched quotes
- candidate before/after hashes, review state (`pending`, `approved`, or `rejected`), and remaining follow-ups

Keep credentials, account identifiers, and copied shell snippets out of the artifact. A failed fetch is a price-stage blocker; it does not roll an already completed imported statement back from `done`.
