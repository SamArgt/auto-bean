# Price Run And Artifact Contract

Apply this contract to every Beanprice fetch.

## Fetch modes

- `snapshot`: Use for import epilogues and normal updates. Choose one explicit target date and run `./.venv/bin/bean-price --date <target-date> ledger.beancount` without `--update`.
- `historical_backfill`: Use only when the user explicitly requests historical coverage. Dry-run the exact `--update` command first and record its target date range and job count before executing it live.

Use Beanprice's default worker count unless the user explicitly requests a concurrency change.

## Completion and reconciliation

Run the live command with verbose logging so redundant directives and provider failures are observable. If the command returns a running session identifier, poll the same session until it exits. A running session, an initial empty chunk, or partial stdout is not a completed command.

Classify the run only after receiving its terminal exit code:

- `succeeded`: exit code is zero, no provider error is present, and every dry-run job is accounted for by an emitted directive or an explicitly logged redundant directive.
- `no_op`: exit code is zero and either the dry run contained no jobs or every job was explicitly logged as redundant.
- `failed`: exit code is nonzero, stderr contains a provider error, or one or more dry-run jobs remain unaccounted for.

Zero emitted directives alone is not success or failure. It is a valid `no_op` only when the reconciliation above accounts for every job. Do not draft fallback directives or run narrower probes while the original command is unresolved, and never describe an unresolved run as completed.

## Price artifact

Create or update the price artifact before returning. Record:

- fetch mode and target date or historical date range
- dry-run job count
- terminal completion state and exit code
- start time, end time, and duration
- emitted directive count and redundant/ignored count
- sanitized stderr summary, including provider warnings or errors
- reconciled job count and any unaccounted jobs
- changed price files or explicit skipped mutation

Keep credentials, account identifiers, and copied shell snippets out of the artifact. A failed fetch is a price-stage blocker; it does not roll an already completed imported statement back from `done`.
