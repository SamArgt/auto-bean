# Categorization Review: Example Bank Checking, March 2026

- Source: `statements/parsed/example-bank-checking-2026-03.json`
- Raw statement: `statements/raw/example-bank/checking-2026-03.pdf`
- Artifact prefix: `checking-2026-03`
- Status id: `example-bank-checking-2026-03`
- Prepared by: `$auto-bean-categorize`

## Fill These In

Mark one choice or fill the blank. Leave blank if unknown.

### Q1

`2026-03-04` `SQ *BLUE BOTTLE COFFEE` `-6.25 USD`

Suggestion: `Expenses:Food:Coffee` (medium)
Evidence: web search for `Blue Bottle Coffee San Francisco`; nearby transactions support San Francisco. Source: official merchant site.

- [ ] use suggestion
- [ ] use: `____________________________`
- [ ] skip for now

Note: `____________________________`

### Q2

`2026-03-07` `ONLINE TRANSFER TO SAV 8842` `-500.00 USD`

Suggestion: likely transfer to `Assets:Bank:Savings`

- [ ] transfer to suggested account
- [ ] categorize as: `____________________________`
- [ ] not sure

Note: `____________________________`

## Categorized Transactions Ready For Posting

- T3: `2026-03-09` Payroll deposit `2,400.00 USD` -> `Income:Salary` (high)
- T4: `2026-03-12` Electric utility `-92.41 USD` -> `Expenses:Utilities:Electric` (high)

## Reconciliation And Deduplication Findings

- R1: `likely_transfer`; `ONLINE TRANSFER TO SAV 8842` may match the savings deposit. Needs Q2.

## Import Batch Cross-Statement Review

This section is appended or updated by `$auto-bean-import` only when another statement in the same import batch may be the matching transfer or duplicate side.

- X1: possible cross-statement transfer with `.auto-bean/artifacts/categorize/savings-2026-03--categorize.md` T7; same `500.00 USD`, nearby date, opposite cash movement. Needs Q2.

## Memory Suggestions

- `category_mapping`: `SQ *BLUE BOTTLE*` -> account chosen in Q1
- `transfer_detection`: `ONLINE TRANSFER TO SAV ****` -> confirmed internal transfer pattern from Q2
