---
name: auto-bean-apply
description: Apply posting and reconciliation work for exactly one assigned parsed statement or intermediate import artifact. Use only as a bounded internal stage for `$auto-bean-import`; do not discover import work, finalize the full import, commit, push, or mark statements done.
---

Use this only for the parsed-evidence-to-working-tree stage assigned by `$auto-bean-import`.

Inputs from `$auto-bean-import`:

- one parsed statement file or one explicit intermediate import artifact
- the matching `statements/import-status.yml` entry
- any relevant memory hints, reconciliation context, or user answers already approved for this artifact

Read when needed:

- `.agents/skills/shared/memory-access-rules.md` before using governed memory hints
- `.agents/skills/auto-bean-apply/references/reconciliation-findings.md` for transfer, duplicate, balance, currency, or future-transfer findings
- `.agents/skills/auto-bean-apply/references/clarification-guidance.md` before asking for user clarification

Workflow:

1. Confirm the assigned scope:
   - handle only the assigned parsed/intermediate artifact
   - do not scan for other parsed files or raw statements
   - do not decide which artifact should run next
2. Prepare postings for this artifact:
   - use `$auto-bean-query` for ledger reads, duplicate checks, account activity, balances, or transaction existence
   - use governed memory only as advisory evidence
   - use `$auto-bean-write` for transaction drafting or correction
3. Reconcile only this artifact's drafted result:
   - surface `likely_transfer`, `possible_duplicate`, `unbalanced`, `currency_risk`, or `possible_future_transfer` findings when supported by evidence
   - fail closed instead of guessing when interpretation is materially ambiguous
4. Update only this artifact's status:
   - set `in_review` after import-derived transactions for this artifact are written
   - keep `parsed` or `parsed_with_warnings` when posting work is blocked or not started
   - never set `done`
5. Validate mutations for this artifact:
   - use the validation path from `$auto-bean-write` for transaction changes
   - revalidate if reconciliation decisions change drafted postings
6. Return control to `$auto-bean-import` with:
   - assigned parsed/intermediate artifact path
   - ledger edits made for this artifact
   - status change for this artifact
   - reconciliation findings and suggested actions
   - validation result
   - whether user input is required, and the exact question/reason
   - possible reusable learning for `$auto-bean-import` to consider

Guardrails:

- Do not discover, batch, or orchestrate import work.
- Do not mark statements `done`.
- Do not request commit or push approval.
- Do not write `.auto-bean/memory/**`; report possible reusable learning back to `$auto-bean-import` so it can decide whether to invoke `$auto-bean-memory`.
- Do not apply a finding decision without an explicit user answer routed by `$auto-bean-import`.
