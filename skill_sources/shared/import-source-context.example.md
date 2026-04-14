# Import Source Context Example

Use this template when you want to preserve bounded, reviewable source-context memory for a statement source. Keep it advisory-only, keep it narrow, and leave out anything that tries to replace current evidence.

## Pre-fill

Fill these fields before saving a source-context note:

- `context_id`:
- `source_slug`:
- `institution_name`:
- `statement_format`:
- `account_mask`:
- `statement_descriptor`:
- `storage_path`:
- `last_reviewed_at`:
- `created_at`:
- `updated_at`:

## Source Identity

This note describes the statement source identified by `source_slug` at `institution_name`. The current known format is `statement_format`, and the recognizable account fragment is `account_mask`.

Use `statement_descriptor` for the exact institution wording, heading, or label that makes this source easy to recognize during future imports.

## Statement-Shape Hints

Record only the layout clues that are stable enough to reuse:

- Date column labels:
- Amount column labels:
- Balance column label:
- Other recurring headers or layout markers:

## Account-Structure Reuse Hints

Record only structure hints that were supported by the reviewed import outcome:

- Primary account:
- Counterparty branch:
- Operating currency:
- Other minimal account-opening hints:

## Parser Guidance

Keep parser guidance practical and bounded. Prefer short notes over rigid schemas.

- Preferred source format:
- Parse statuses that are safe to reuse:
- Known parser warnings to expect:
- Conditions that should block reuse:

## Review Metadata

This context is advisory only. It should help future review, not override the current statement evidence, ledger state, validation, or approval boundaries.

- Storage path:
- Review required: [ ]
- Derived from import status: [ ]
- Reuse is advisory only: [ ]

## Reviewer Checklist

- [ ] Source identity still matches the current statement evidence.
- [ ] Statement-shape hints reflect repeated patterns, not a one-off artifact.
- [ ] Account-structure hints are still valid against the current ledger.
- [ ] Parser guidance is specific enough to help and narrow enough to avoid overreach.
- [ ] No transaction-posting memory, categorization memory, or open-ended preferences were added.
- [ ] Timestamps and review notes were refreshed after the latest trusted outcome.

## Optional Review Notes

Add a short paragraph here if a future reviewer would benefit from brief context about why these hints were kept, updated, or intentionally limited.
