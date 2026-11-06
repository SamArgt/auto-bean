# Import review experiment

This experiment renders the plugin's React components and CSS directly. There is no separate review UI to keep in sync. A demo bridge adapts the synthetic JSON store to the plugin's read and save calls. It never reads a live ledger or notifies an agent.

From the repository root, build with Node 24 or later:

```sh
npm --prefix frontend/import-review run build:demo
uv run python experiments/review-ui-design/serve.py
```

Open http://127.0.0.1:8767/. Rebuild and reload after frontend changes. The plugin bundle uses `npm --prefix frontend/import-review run build`.

## Try the review

- Choose an account in the sidebar. Accounts with no session transactions are hidden there. Their mapping and balance evidence stays in Session.
- Approve the most likely category directly in its transaction row.
- Open a transaction to see one category per line, or select **Something else** to type an answer.
- Watch the spinner while a save is pending. Saves have a 0.9-second delay.
- After saving, the row shows **Input received**. Sidebar counts show remaining and received inputs. The answer still needs an agent review.
- Open Price to see **New commodity** highlights for VWCE, including its price job.
- Expand **Demo settings** to change the theme, simulate a failed save, inspect saved JSON/diffs, or reset the fixture stage.

| URL | Data |
| --- | --- |
| `/` | Three statements, 15 transactions, transfers, splits, fees and prices |
| `/?stage=accounts` | Account mapping questions with no transactions |
| `/?stage=mixed` | Extraction failure, account question and balance mismatch |

The experiment saves schema-validated copies in `.demo-state/<stage>/`. Refresh preserves answers. Reset restores the stage's fixtures. The seed data and reported balances stay unchanged.

The shared UI uses the same stale-edit tokens, draft guards and save controls as the plugin. The adapter simulates batch sending. It does not simulate an agent pass, ledger writing, validation recovery or HTML export. Use **Saved JSON / diffs** to inspect experiment saves. Transaction category suggestions are complete account names, ordered from most to least likely. Legacy prose stays in evidence and is not converted into a category approval.

## Checks

```sh
node --test experiments/review-ui-design/model.test.mjs experiments/review-ui-design/bridge.test.mjs
npm --prefix frontend/import-review test
uv run pytest tests/test_review_demo.py
```
