# Import Price Update

Use after import write/final-review decisions and memory handoff. This is an import epilogue that updates valuation context without advancing statement status.

1. Invoke `$auto-bean-prices` once:
   - pass import context, changed ledger files, imported account/commodity hints, validation status, and relevant import artifact paths
   - instruct it to update active held commodities plus commodities touched by this import
   - instruct it not to ask the user directly when invoked by import
2. Broker price-source questions:
   - if `$auto-bean-prices` reports unknown or conflicting source mappings, ask bounded questions in the main thread
   - keep price blockers separate from statement posting blockers; do not move `done` statements backward solely because a price source is missing
   - route approved reusable source mappings to `$auto-bean-memory` as `commodity_price_source` suggestions
3. Include price results in the final import summary:
   - price artifact path
   - changed price files or skipped mutation
   - commodities priced and skipped
   - validation result after price directives
   - memory suggestions or memory write result
