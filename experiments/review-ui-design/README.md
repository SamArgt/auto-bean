# Import review prototype

Static HTML, CSS and JavaScript with synthetic JSON fixtures. The experiment does not use workspace templates. No live ledger, MCP calls or real agent notifications are used.

Run from the repository root:

```sh
uv run python experiments/review-ui-design/serve.py
```

Open http://127.0.0.1:8767/.

## Layout

The left sidebar contains Session, Account and Price. Individual source accounts stay visible beneath Account, with counts for outstanding inputs.

- **Session:** expand a statement group to see its sources, accounts, opening and closing balances, current questions and available statement approval.
- **Account:** choose a source account from the left sidebar. Filter transactions by needed input or internal transfers, or search. Open a row to respond, edit postings, splits, fees and simple unit costs/prices, or follow a linked transfer.
- **Price:** inspect and approve the separate price run.

The fixed footer shows outstanding inputs and saved changes. Saves write schema-validated synthetic JSON copies under `.demo-state/<stage>/` immediately. Send is enabled only when all current questions have responses, available statement/price approvals are saved, and no drafts remain. It simulates one notification and retains the last batch on disk. Refresh preserves saved edits. **Saved JSON / diffs** shows the current files and the before/after diff for each save. **Reset demo** restores that stage from its original fixtures and clears its history.

Transaction, account and balance choices come from the inline `review.suggestions` arrays. Account suggestions name a ledger account. Balance suggestions request an agent check; they do not authorize an adjustment. Each input shows its rationale first, then a suggestions dropdown and **Save choice**. Select **Something else** in the dropdown to enter a correction. The interface uses slate surfaces, blue actions and amber input indicators.

Account mappings, clarification answers and postings update their inline review fields in the copied parsed-group JSON. Price approvals update the copied session JSON. Batch bookkeeping and diffs live in `batch.json`. Seed fixtures and reported balances remain unchanged. Send clears the pending queue and increments the simulated notification count; it makes no MCP call. The server checks the save token to reject stale tabs.

A clarification response does not advance the group, convert held postings into accepted postings, or create validation evidence. An agent pass is still needed. Approval is available for complete, categorized source sections, even if another member blocks the group. Editing postings invalidates that statement's saved approval. Shared transfer postings remain read-only and identify one posting owner. The batch gate includes all available statement approvals.

## Fixtures and current contracts

Fixtures follow the product schemas under `plugins/auto-bean/references/schemas/` and the flow in `plugins/auto-bean/references/import-review.md`:

- `session.json`: session schema v1, group identities, names, origins, memberships, parsed paths and price runs.
- `import-status.json`: JSON representation of the status YAML schema v1. Lifecycle state belongs to each group; fingerprints and retries belong to its source map.
- `statements/parsed/banking-october.json`: parsed-group schema v2 with checking and savings source sections.
- `statements/parsed/investments-october.json`: parsed-group schema v2 with the brokerage source section.

The loader checks exact group membership, unique source ownership, parsed paths, source fingerprints, account IDs and reciprocal transfer links. It supports multiple accounts in each statement. Source data is not embedded in the HTML.

Use **Demo settings** to choose a fixture set:

| URL | Available data |
| --- | --- |
| `/` | Three statements, 15 transactions, two internal transfer pairs, splits, tax, fees, unit cost and a price quote |
| `/?stage=accounts` | Account mapping questions; transactions and closing balances unavailable |
| `/?stage=mixed` | A source extraction failure, an account question and an opening-balance mismatch |

The group stays at its saved stage while responses await the agent. Unavailable amounts are never displayed as zero. Quotes are illustrative, not market data. The prototype does not simulate ledger writing, stale validation recovery or import completion.

## Checks

```sh
node --test experiments/review-ui-design/model.test.mjs
node --check experiments/review-ui-design/app.mjs
```

All 12 JSON fixtures were validated against the current product JSON Schemas, including date formats. Browser checks cover the three tabs, needed-input filtering, split editing and batch sending in the account-only stage.
