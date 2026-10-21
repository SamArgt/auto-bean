# Ledger reference

Use the relevant section: [queries](#querying), [direct mutation review](#direct-review), [directives and postings](#directives), or [commodities](#commodities). Launcher and shared ownership rules are in [common guidance](common.md). Import changes follow [the Import and Write skills](../skills/auto-bean-import/SKILL.md); the direct-review procedure below applies to standalone transaction, price and setup-option requests.

## Querying

Use one-shot `auto_bean bean-query ledger.beancount 'SELECT ...'` calls for bounded answers. Inspect actual account names before choosing exact or regex filters. These patterns are exercised by the packaged smoke check; consult current Beanquery/Beancount documentation through Context7 when syntax or reporting semantics remain unclear.

### Balances by account

```sql
SELECT account, sum(position)
WHERE account ~ "Assets"
GROUP BY account
ORDER BY account;
```

### Holdings and cost basis

```sql
SELECT account, units(sum(position)), cost(sum(position))
GROUP BY account
ORDER BY account;
```

`sum(position)` returns inventories. `units(...)` expresses holdings and `cost(...)` cost basis; neither is automatically market value. Report each commodity separately rather than reducing a mixed inventory to one scalar.

### Account register

```sql
SELECT date, payee, narration, position, balance
WHERE account = "Assets:Bank:Checking"
ORDER BY date;
```

`balance` is the running inventory for the selected rows.

### Account family activity

```sql
SELECT date, account, narration, position, balance
WHERE account ~ "Expenses:Food"
ORDER BY date;
```

### Period summary

```sql
SELECT account, sum(position)
FROM OPEN ON 2026-01-01 CLOSE ON 2026-04-01
WHERE account ~ "Income|Expenses"
GROUP BY account
ORDER BY account;
```

This includes January 1 through March 31: `OPEN ON` includes its date and `CLOSE ON` excludes its date. Use explicit posting-date filters for activity-only reports. Explain the reporting window when material; empty output may reflect a wrong filter rather than no activity.

### Monthly breakdown

```sql
SELECT year, month, account, sum(position) AS total
WHERE account ~ "Expenses"
GROUP BY year, month, account
ORDER BY year, month, account;
```

## Direct review

For a directly requested edit, present review in the conversation; do not require a separate mutation artifact. Imports review parsed postings before writing, then validate actual ledger coverage and balances under the import contract.

1. Inspect Git status and the relevant staged, unstaged and untracked changes. Capture target paths, before SHA-256 hashes (`null` for absent files), exact proposed hunks, and recoverable original contents in the active execution context. Git HEAD alone does not preserve user changes. Validate the baseline ledger; an existing failure needs a bounded repair decision before drafting.
2. With one ledger writer, recheck before hashes, draft the narrow authorized changes, run `auto_bean validate --workspace "$AUTO_BEAN_WORKSPACE"`, and inspect the focused diff. Record after hashes. A failed draft stays visible and blocks later mutations until repaired or resolved. Queries must disclose and exclude unapproved drafts when deciding accepted balances or duplicates.
3. Present evidence, changed files/hunks, validation, reconciliation and unresolved risks. Approval binds those hunks and after hashes. Recheck hashes and validation before acceptance; changed drafts need renewed review, unchanged drafts do not need repeated permission. Commit only authorized paths/hunks when requested; never stage the whole workspace. Push requires authorization.
4. On rejection, remove only the draft's hunks if current contents still match. Preserve unrelated and overlapping user edits. Missing baselines or overlapping changes require a concrete conflict resolution; never reset, stash or restore whole files blindly. Validate what remains; rejection is not completion.

On a fresh chat or interrupted write, recover the existing diff, source fingerprint and source/account/record provenance before drafting again. Complete or repair the same draft; never append it twice. If its original hunks or ownership cannot be recovered, ask before undoing anything.

## Directives

Reuse the ledger's include graph, configured top-level account names (`option "name_*"` may customize them), file layout, quoting and metadata conventions. Do not reorganize includes or rename account roots incidentally. Open accounts by the first posting date, respect close dates, and treat declared currency restrictions as validation constraints.

```beancount
2026-01-01 open Assets:Checking USD,EUR
2026-02-01 balance Assets:Checking 100.00 EUR
2026-01-31 document Assets:Checking "statements/raw/checking/jan-2026.pdf"
2026-01-31 note Assets:Checking "Reconciled against statement"
```

A `balance` assertion checks units at the **beginning** of its date, for one commodity. A January 31 closing balance therefore uses February 1. Assertions do not replace missing transactions. Document/note directives provide evidence without affecting balances; avoid identical date/account/file document duplicates. Import owns statement-document dating and mapping decisions.

Prefer explicit balanced postings. Preserve source payees and narration without guessing; keep distinct purchases separate. Tags (`#food`) and links (`^statement`) belong on the transaction header, while indented metadata belongs to the entry or posting it describes.

```beancount
2026-01-15 * "Coffee Shop" "Card purchase" #food ^stmt-2026-01
  id: "stmt-2026-01-15-0004"
  Liabilities:US:Visa:Gold -4.75 USD
  Expenses:Food:Coffee 4.75 USD

2026-02-01 * "Broker" "Buy shares"
  Assets:Brokerage:HOOL 10 HOOL {498.45 USD}
  Assets:Brokerage:Cash -4984.50 USD

2026-02-10 * "FX trade" "EUR conversion"
  Assets:Bank:EUR 100.00 EUR @ 1.08 USD
  Assets:Bank:USD -108.00 USD
```

Lot costs (`{...}`) and transaction prices (`@ ...`) require source evidence. For direct entries, at most one amount may be omitted when its intended value is unambiguous; import posting proposals require explicit amounts. Reuse suitable accounts instead of creating duplicate siblings. Optional `pad`, `custom`, `event`, saved `query`, plugin and option changes need a justified owning workflow, not routine transaction cleanup.

## Commodities

```beancount
2026-01-01 commodity HOOL
  name: "Hooli Inc."
  asset_class: "Stock"

2026-01-15 price HOOL 510.00 USD
```

Follow ledger symbol and metadata conventions. Common currencies need no explicit `commodity` declaration unless metadata or local conventions require one. Reuse existing declarations; date a needed new declaration using the ledger convention or earliest use. Present exact non-common commodity and price directives for explicit approval before writing them.

Market prices support valuation; an unavailable external quote does not prevent recording evidenced holdings at supported cost. Route price-source selection and fetching to `$auto-bean:auto-bean-prices`. Record only supported costs/prices, and do not silently resolve currency conflicts by changing account constraints.
