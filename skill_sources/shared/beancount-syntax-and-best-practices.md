# Beancount Syntax And Best Practices

Purpose: Beancount syntax, ledger structure, and mutation safety only. Workflow questions, import status, and memory handling live in their own shared references.

## Core rules

- Reuse the workspace's existing root account names, include graph, quoting style, and file layout.
- SHOULD prefer explicit postings and directives over shorthand.
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

## Commodities

```beancount
2026-01-01 commodity HOOL
  name: "Hooli Inc."
  asset_class: "Stock"

2026-01-15 price HOOL 510.00 USD

2000-01-01 commodity AAPL
  price: "USD:yahoo/AAPL" # Use price metadata for bean-price integration when possible
```

- Commodity symbols are Beancount units such as `USD`, `EUR`, `BTC`, `HOOL`, or other ledger-defined assets; use uppercase commodity names and follow the ledger's existing naming style.
- Common currencies and currency-like commodities such as `USD`, `EUR`, and `GBP` do not need explicit `commodity` declarations unless the ledger already declares them or needs metadata.
- Commodities other than common currencies MUST be declared with a `commodity` directive and accompanied by a relevant `price` directive.
- Use `commodity` directives as the canonical place for commodity metadata such as human-readable names, asset class, issuer, region, or other fields the ledger already tracks.
- When declaring a new commodity, use the price metadata field to link to an exact beanprice source when possible. Probe candidate source strings with `./.venv/bin/bean-price -e 'USD:yahoo/AAPL'`, and use web search only to discover or verify the correct beanprice source string when the commodity is ambiguous.
- Reuse existing commodity declarations and metadata keys before adding a new declaration.
- Choose declaration dates that match the ledger's convention; if there is no local convention, use the earliest date the commodity is needed or a stable opening date for the ledger.
- When a non-common commodity is needed, SHOULD suggest the exact `commodity` and `price` directives in the agent conversation, but MUST ask for explicit user approval before writing them.

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
- Header data should contain a human readable payee and narration when the ledger's style expects them, even if they could be inferred from metadata or tags.
- Avoid generic payees like "Card purchase" when the statement provides a clearer name, but do not guess when the statement is ambiguous.
- Common flags are `*` for cleared and `!` for needs-attention.
- Tags use `#tag`; links use `^link`; both belong on the transaction header.
- Metadata is written as indented `key: value` pairs under the entry or posting it describes.
- Postings may include units, lot cost `{...}`, price `@ ...`, metadata, and an optional posting flag.
- SHOULD prefer explicit balancing amounts even though Beancount can infer one missing amount.
- Leave at most one posting amount omitted, and only when the intended balance is unambiguous.
- Only emit costs or prices when the source evidence clearly supports them.
- Preserve the ledger's established metadata keys, quoting style, and posting order.
- Compare against nearby ledger entries before finalizing likely duplicate or transfer-shaped postings.

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
- If a posting would violate declared account currencies, ask and wait when intent is unclear, or add the minimum justified supporting directive when evidence is strong.
- Reuse the existing file placement pattern for similar transactions instead of moving entries between files without a strong reason.
- Keep edits narrow and validate after every mutation.
