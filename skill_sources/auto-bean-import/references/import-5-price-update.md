# Import Price Update

Use after import-owned ledger writes and their current final-review decisions, before the consolidated memory handoff. On resume, also handle pending price follow-ups recorded in prior artifacts. Skip fetching when this invocation made no import-owned ledger writes and has no pending price follow-up. This epilogue updates valuation context without advancing statement status; pass its results and source-memory suggestions to stage 6 even when fetching is blocked.

1. Invoke `$auto-bean-prices` once:
   - pass import context, changed ledger files, imported account/commodity hints, validation status, and relevant import artifact paths
   - instruct it to update active held commodities plus commodities touched by this import
   - instruct it to use one explicit dated snapshot without `--update`; an import epilogue is not a historical backfill request
   - instruct it not to ask the user directly when invoked by import
2. Broker price-source questions:
   - if `$auto-bean-prices` reports unknown or conflicting source mappings, ask bounded questions in the main thread
   - keep price blockers separate from statement posting blockers; do not move `done` statements backward solely because a price source is missing
   - require a terminal fetch state and reconciled job telemetry before accepting success or no-op; a running session or initial empty output is incomplete
   - route approved reusable source mappings to `$auto-bean-memory` as `commodity_price_source` suggestions
3. Include price results in the final import summary:
   - price artifact path
   - fetch mode, terminal completion state, exit code, duration, dry-run job count, directive count, redundant/ignored count, and sanitized stderr summary
   - changed price files or skipped mutation
   - commodities priced and skipped
   - validation result after price directives
   - memory suggestions or memory write result
