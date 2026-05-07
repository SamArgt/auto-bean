# Import Account Inspection

Use for first-seen account derivation and opening-balance checks.

## 1. First-Seen Account Structure

- For each statement at `account_review`, inspect existing ledger accounts with `$auto-bean-query`.
- Read relevant `import_source_behavior` memory selected during discovery or reported by `$auto-bean-process`.
- Classify inferred accounts as `existing_account`, `first_seen_candidate`, or `blocked_inference`.
- Consider only banking, credit card, loans, cash, and investment account types for first-seen structure inference.
- Infer only institution-owned balance-sheet accounts and opening balances; leave expense, income, and other transaction categories to `$auto-bean-categorize`.
- Infer Beancount-safe account names and minimal supporting directives only when current facts meet the shared strong-evidence threshold.
- Before writing directives, present exact proposed directives, target file, supporting parsed evidence, and reason the account appears first-seen. Ask the user to approve or correct it.
- Set `account_blocked` while required account identity, currency, mutation-target, duplicate-risk, or approval questions are unresolved.
- Write only approved account-opening structure and minimal supporting directives, preferring `beancount/accounts.beancount` and `beancount/opening-balances.beancount`.
- Validate with `./scripts/validate-ledger.sh` or `./.venv/bin/bean-check ledger.beancount`.
- Record proposed, approved, rejected, or written first-seen decisions in the import-owned artifact.
- Move resolved `account_review` or `account_blocked` statements to `balance_review`.
- Gate: continue to opening-balance checks only if ALL statements are at `balance_review`. Wait for user answers for `account_blocked` or `account_review` statements before advancing to opening-balance checks.

## 2. Opening Balance Checks

- For each statement at `balance_review`, compare parsed opening balances against ledger balances up to the statement start date using `$auto-bean-query`.
- If balances mismatch, surface a bounded question with ledger balance, statement opening balance, account details, and remediation options.
- Set `balance_blocked` while required balance-remediation input is unresolved.
- Record the decision in the import-owned artifact.
- Move resolved `balance_review` or `balance_blocked` statements to `categorize_ready`.
- Keep unresolved balance discrepancies out of categorization.
- Gate: continue to categorization only if ALL statements are at `categorize_ready`. Wait for user answers for `balance_blocked` or `balance_review` statements before advancing to categorization.
