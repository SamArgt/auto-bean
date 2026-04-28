# Reconciliation And Deduplication Guidance

Use this reference to reason about Beancount-safe reconciliation findings.
Keep it focused on ledger evidence and finding quality, not workflow actions.

## Beancount-grounded checks

- Transactions must balance once posted. Treat a category/account suggestion that cannot support a balanced transaction as a real finding, not a cosmetic issue.
- Beancount can sometimes infer one missing amount, but categorize should still produce explicit posting inputs for `$auto-bean-import` to pass to `$auto-bean-write`.
- `open` directives may declare allowed currencies for an account. A suggested posting account outside those currencies is a `currency_risk`.
- `balance` directives act as checkpoints against missing or duplicated transactions. Use them as supporting evidence when they exist.

## Finding categories

- `likely_transfer`: two sides are both present strongly enough to review together.
- `possible_future_transfer`: one side looks transfer-like, but no counterpart matches yet.
- `possible_duplicate`: a parsed transaction or suggested posting input may already exist in the ledger or be duplicated in the same run.
- `unbalanced`: the suggested posting inputs cannot balance from explicit evidence.
- `currency_risk`: an account constraint, usually from `open`, makes the suggested posting account unsafe.

## Evidence to compare

- Parsed statement facts: dates, amounts, currencies, institution account identity, statement references, imported ids.
- Suggested posting inputs: account paths, payee or narration, links, metadata, and sign of cash movement.
- Existing ledger entries: nearby dates, same amount and currency, same external id, similar payee stem, and matching account intent.
- Ledger constraints: `open` directives, known account structure, and any nearby `balance` assertions.

## Conservative matching rules

- Prefer exact amount and currency matches before weaker narration similarity.
- Treat imported ids, links, and stable metadata as stronger duplicate signals than plain-text descriptions.
- For transfers, look for opposite cash movement, nearby timing, and account context that suggests the same owner moved funds internally.
- For duplicates, compare both against existing ledger history and same-run parsed or categorized candidates.
- Do not treat a normal recurring payment as a duplicate just because the merchant and amount look familiar.
- Do not assume a transfer match when only one side is visible and the counterpart account remains unclear.

## Output shape

Each finding should stay reviewable and cite:

- `finding_type`
- `candidate_scope`
- `summary`
- `evidence`

## Example

```md
- finding_type: possible_duplicate
  candidate_scope: cand-011
  summary: Drafted transaction closely matches an existing booking.
  evidence:
  - same amount `48.21 USD`
  - same imported id `bank-2026-02-18-4821`
  - existing ledger transaction dated `2026-02-18`
```
