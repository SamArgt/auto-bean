# Beancount Syntax And Best Practices

Use this reference when authoring or reviewing Beancount ledger edits. Keep changes deterministic, minimal, explicit, and easy to review.

## Core rules

- Reuse the workspace's existing root account names, include graph, quoting style, and file layout.
- Fail closed when account identity, currency, balancing intent, or mutation target is ambiguous.
- Prefer explicit postings and directives over shorthand.
- Avoid duplicate directives, duplicate transactions, and silent rewrites of history.
- Treat balancing failures and `open` directive currency restrictions as hard safety checks, not soft suggestions.

## Common directives

```beancount
YYYY-MM-DD open Assets:Checking USD,EUR
YYYY-MM-DD close Assets:Checking
YYYY-MM-DD commodity USD
YYYY-MM-DD balance Assets:Checking 100.00 USD
YYYY-MM-DD note Assets:Checking "Reconciled against bank portal"
YYYY-MM-DD document Assets:Checking "statements/2026-01.pdf"
YYYY-MM-DD price HOOL 510.00 USD
YYYY-MM-DD event "location" "Paris"
YYYY-MM-DD query "cash_balances" "SELECT account, sum(position) WHERE account ~ 'Assets'"
YYYY-MM-DD custom "import_marker" Assets:Checking "statement-2026-01"
```

- Treat currencies on `open` directives as hard posting constraints.
- Use `balance` for assertions, not to replace missing transactions.
- Use `note`, `document`, and metadata for audit context without changing balances.
- Avoid adding `custom`, `event`, `query`, `price`, `pad`, or plugins unless the ledger already uses them or the change clearly requires them.

## Transactions and postings

```beancount
2026-01-15 * "Coffee Shop" "Card purchase" #food ^stmt-2026-01
  id: "stmt-2026-01-15-0004"
  Liabilities:US:Visa:Gold  -4.75 USD
  Expenses:Food:Coffee       4.75 USD

2026-02-01 * "Broker" "Buy shares"
  Assets:Brokerage:HOOL      10 HOOL {498.45 USD}
  Assets:Brokerage:Cash   -4984.50 USD

2026-02-10 * "FX trade" "EUR conversion"
  Assets:Bank:EUR           100.00 EUR @ 1.08 USD
  Assets:Bank:USD          -108.00 USD
```

- Header shape is `DATE [txn|FLAG] [[PAYEE] NARRATION]`.
- Common flags are `*` for cleared and `!` for needs-attention.
- Tags use `#tag`; links use `^link`; both belong on the transaction header.
- Metadata is written as indented `key: value` pairs under the entry or posting it describes.
- Postings may include units, lot cost `{...}`, price `@ ...`, metadata, and an optional posting flag.
- Prefer explicit balancing amounts even though Beancount can infer one missing amount.
- Leave at most one posting amount omitted, and only when the intended balance is unambiguous.
- Only emit costs or prices when the source evidence clearly supports them.
- When import-derived postings resemble transfers or duplicates, surface the evidence for review instead of silently netting or deleting entries.

## Account naming

```beancount
Assets:US:BofA:Checking
Liabilities:US:Amex:Platinum
Income:US:Employer:Salary
Expenses:Food:Groceries
Equity:Opening-Balances
```

- Accounts are colon-separated hierarchies rooted at configured top-level names such as `Assets`, `Liabilities`, `Equity`, `Income`, and `Expenses`.
- Reuse the ledger's configured top-level names; they may be customized with `option "name_*" ...`.
- For institutions, prefer stable paths like `Type:Country:Institution:Account` when the ledger already follows that style.
- For expenses, prefer semantic categories over institution-specific paths unless the ledger already models them differently.
- Do not create a new sibling account when an existing account already matches the institution, instrument, and currency intent.

## Options and safe edits

```beancount
option "title" "Personal Ledger"
option "name_assets" "Assets"
include "beancount/accounts.beancount"
plugin "beancount.plugins.currency_accounts" "Equity:CurrencyAccounts"
```

- Put parser-affecting options near the beginning of the root ledger file.
- Do not add or rewrite root account-name options unless the user explicitly wants a ledger-wide rename.
- Respect the current include graph instead of reshuffling files.
- Inspect existing `open` directives before posting into an account.
- If a posting would violate declared account currencies, stop or add the minimum justified supporting directive.
- Keep edits narrow, validate after every mutation, and present diffs instead of guessing through uncertainty.
