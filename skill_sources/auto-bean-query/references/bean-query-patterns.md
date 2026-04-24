# Bean Query Patterns

Use this reference when translating a natural-language ledger question into `bean-query`.

Read Context7 Beancount docs before relying on unfamiliar BQL details. This file is a compact working guide, not the authority.

## Quick rules

- Prefer `bean-query ledger.beancount 'SELECT ...'` for direct answers.
- Keep account filters explicit with exact names or `account ~ 'Pattern'`.
- Start with grouped summaries, then move to detail rows if the user asks why or where a number came from.
- Remember that `position` and `balance` can be inventories, not plain scalar values.

## Common query shapes

### Balance by account

```sql
SELECT account, sum(position)
WHERE account ~ "Assets"
GROUP BY account
ORDER BY account;
```

Use when the user wants balances or grouped totals without lot or cost expansion.

### Commodity-aware balances

```sql
SELECT account, units(sum(position)), cost(sum(position))
GROUP BY account
ORDER BY account;
```

Use when `sum(position)` would hide multiple lots or commodities inside an inventory.

### Register for one account

```sql
SELECT date, payee, narration, position, balance
WHERE account = "Assets:Bank:Checking"
ORDER BY date;
```

Use when the user wants to inspect activity, running balances, or recent changes in one account.

### Account activity by pattern

```sql
SELECT date, account, narration, position, balance
WHERE account ~ "Expenses:Food"
ORDER BY date;
```

Use regex matching for families of accounts when the workspace naming is stable.

### Period summary

```sql
SELECT account, sum(position)
FROM OPEN ON 2026-01-01 CLOSE ON 2026-03-31
WHERE account ~ "Income|Expenses"
GROUP BY account
ORDER BY account;
```

Use reporting windows when the user asks for a period statement, not just postings whose transaction dates fall in a range.

### Monthly breakdown

```sql
SELECT year, month, account, sum(position) AS total
WHERE account ~ "Expenses"
GROUP BY year, month, account
ORDER BY year, month, account;
```

Use when the user wants trends over time rather than a single total.

## Interpretation notes

- `sum(position)` returns inventories. That is often correct, but it may surprise users expecting one currency.
- `units(...)` is better when the question is about raw holdings.
- `cost(...)` is useful for cost basis, not market value.
- `balance` in register-style output is a running inventory balance for the selected rows.
- `FROM OPEN ON ... CLOSE ON ...` changes reporting semantics. Use it intentionally and explain it when relevant.
- Empty output can mean no matches, the wrong account pattern, or a reporting window that excluded the data.

## Shell ergonomics

- `bean-query ledger.beancount` opens the interactive shell.
- The shell supports `set` options for formatting such as `format`, `boxed`, `spaced`, `pager`, and `expand`.
- Prefer one-shot CLI queries in agent runs unless interactive exploration is clearly more efficient.
