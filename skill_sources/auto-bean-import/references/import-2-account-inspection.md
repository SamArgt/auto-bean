# Import Account Inspection

Use for first-seen account derivation and opening-balance checks.

## 1. Account detection and first-seen structure inference

- For each statement at `account_review`, inspect existing ledger accounts with `$auto-bean-query`.
- Read relevant `import_source_behavior` memory selected during discovery or reported by `$auto-bean-process`.
- Search `.auto-bean/memory/account_mappings.json` for any matching account-mapping memory under the shared strong-evidence threshold.
- Classify inferred accounts as `existing_account`, `first_seen_candidate`, or `blocked_inference`. For `existing_account`, write down their corresponding account in the import-owned artifact.
- For every parsed `statement_metadata.accounts[]` item, derive and write a raw-statement document reference after the statement account is matched to a ledger account:
  - directive shape: `YYYY-MM-DD document <ledger-account> "statements/raw/..."`
  - date: the parsed statement period end date
  - account: the confidently matched ledger account for that parsed statement account
  - path: the parsed statement's `source_file` under `statements/raw/`
  - multi-account statements: write one directive per matched ledger account, all pointing to the same raw file
- If a statement account cannot be matched confidently to a ledger account, the statement period end date is missing, or the raw `source_file` is missing or outside `statements/raw/`, set `account_blocked` and do not advance the statement, because the raw-statement `document` directive would be unsafe to guess.
- Before writing a document directive, deduplicate against the current ledger by exact directive semantics: same date, account, and raw statement path.
- For document directive placement, follow the ledger's existing document-directive placement pattern when present; otherwise write it in the narrowest Beancount file that owns nearby statements or account directives for that account/date.
- Record proposed, approved, reused, rejected, blocked, or written document reference decisions in the import-owned artifact under `## Document Reference Decisions`.
- Surface proposed document directives in the import review/approval package alongside first-seen account decisions when applicable; they are approved by the same import approval gate unless the user explicitly rejects or changes them.
- Consider only banking, credit card, loans, cash, and investment account types for first-seen structure inference.
- Infer only institution-owned balance-sheet accounts and opening balances;
- Infer Beancount-safe account names and minimal supporting directives only when current facts meet the shared strong-evidence threshold.
- Before writing directives, present exact proposed directives, target file, supporting parsed evidence, and reason the account appears first-seen. Ask the user to approve or correct it.
- Set `account_blocked` while required account identity, currency, mutation-target, duplicate-risk, or approval questions are unresolved.
- Write only approved account-opening structure, raw-statement document directives, and minimal supporting directives, preferring `beancount/accounts.beancount` and `beancount/opening-balances.beancount` for account structure.
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
