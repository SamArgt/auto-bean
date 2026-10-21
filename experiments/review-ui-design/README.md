# Review UI design prototype

Serve this folder over HTTP and open `index.html`. The page fetches these synthetic fixtures at startup:

- `fixtures/session.json`: session membership, parsed-file paths, price run and directive.
- `fixtures/import-status.json`: workflow status, source identity and parsed-file association.
- `fixtures/statements/parsed/*.json`: extracted records, account balances, inline review decisions, postings and reciprocal transfer links.

These files follow the product's `session.schema.json`, `status.schema.json`, and `parsed-v2.schema.json`. Production stores import status as YAML; this prototype uses the equivalent JSON object for browser loading. All names, transactions, quotes and source fingerprints are synthetic. No raw bank files or live ledger are accessed. Fingerprints identify synthetic source labels, not real statement bytes.

Edit a fixture and reload the browser to change the initial review. The HTML contains no fallback transaction dataset. Missing files, identity mismatches and invalid reciprocal transfer links show a load error. JSON schemas were checked separately; the browser performs focused identity and link checks, not full schema validation.

The adapter currently supports one source account per statement. It maps the loaded documents into the existing presentation model. Simple posting corrections, approvals and demo outcome controls are in-memory simulations. They never write fixtures or ledger files. Reset reloads the fixture files. Complex postings support in-memory edits to accounts, amounts, currencies, explicit unit costs and unit prices, plus adding/removing lines. Saving requires balanced currency weights and the original statement cash amount. Drafts block approval, persist across navigation, and can be discarded. Saving invalidates the statement’s previous approval. Shared transfer postings remain read-only. Lot dates, labels, total costs and omitted amounts are outside the editor’s supported syntax. Validation is shown as unavailable until supplied in a fixture or simulated with a demo control.

Each transfer uses reciprocal `linked_records` and the same `posting_owner` on both source rows. The UI shows one shared posting set, with navigation to either source row. The fake completion control waits for both statements to be approved.

The production template and runtime are unchanged.

## Batched review and stage previews

Saves enqueue the latest change per subject in browser memory. Only the explicit Send saved changes to agent button simulates notification. It requires every currently requested input across the session to be reviewed, all current final-review/price decisions to be recorded, no unsaved drafts and no simulated snapshot/stale conflicts. It does not require stages that have not started. Sending clears the unsent batch and increments a demo notification counter; no MCP call is made.

The stage selector reloads one of three JSON fixture sets: the default transaction-review fixtures, fixtures/accounts (only mapping review), or fixtures/mixed (account, failed extraction and opening-balance clarification). These use the same product schemas. Early responses are kept as answers pending agent review; they do not simulate progression or ledger writing. Missing account evidence and balances are shown as unavailable. Prices have their own sidebar section, including a no-results-yet state.

These are proposed UI behaviors only. The plugin's per-save notification behavior is unchanged until this design is applied.
