# Candidate review and recovery

Apply this to transaction, account, document, price, and setup-option edits. Direct requests use the conversation; import uses its existing statement artifact. Do not require a separate mutation artifact.

## Before writing

Inspect Git status and the relevant diff, including staged and untracked files. Record existing user changes, target paths, SHA-256 hashes (or `null` for absent files), and the exact proposed hunks. Keep a recoverable copy of affected original content in the active execution context; do not dump full ledgers into artifacts or reset files from Git. A Git baseline alone does not preserve uncommitted user work.

Validate the starting ledger. If it already fails, report the baseline failure and agree on the bounded repair before drafting. Read-only queries may explain partial results with that qualification. On a fresh chat, recover the candidate from existing artifact/context and the working tree; if the original hunk or ownership cannot be recovered, ask before undoing anything.

## Write, validate, and review

Allow one ledger writer at a time. Verify the before hashes immediately before applying the candidate. Draft narrow changes, run `auto_bean bean-check ledger.beancount`, inspect the actual focused diff, and record after hashes. Present evidence, changed hunks/files, validation, reconciliation, and remaining risks directly in conversation.

A failed draft remains visible but blocks subsequent ledger writes. Repair it within the authorized scope or obtain direction; do not let another statement's query treat its unapproved postings as accepted history. Cross-statement queries must disclose and exclude drafts when determining existing duplicates or balances.

Approval applies only to the presented hunks and after hashes. Immediately before acceptance, check those hashes and rerun validation. A changed candidate requires renewed review; an unchanged candidate does not need repeated permission. Import records the approval evidence before proposing `done`. Commit only the approved paths/hunks; never use a broad `git add --all` in an existing ledger. Push requires user authorization.

## Rejection and resume

On explicit rejection, remove only the candidate's hunks when the current content still matches the reviewed candidate. Preserve staged and unstaged user changes, other statements, and unrelated additions. If edits overlap or the baseline is missing, show the conflict and ask for the smallest resolution; never reset, stash, or restore a whole file blindly. Validate the remaining ledger and return the statement to the owning blocked stage; rejection is not `done`.

Before resuming an interrupted write, match source fingerprint and `(source_fingerprint, account_id, record_id)` provenance against existing candidate postings. Complete or repair the same candidate instead of appending it again. A known duplicate has an explicit reviewed disposition linked to the existing transaction. An approved transfer shared by two statements has one posting owner and retains both source-record references.
