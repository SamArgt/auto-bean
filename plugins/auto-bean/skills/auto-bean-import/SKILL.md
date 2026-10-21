---
name: auto-bean-import
description: Import statements from discovery through extraction, account mapping, categorization, user review, ledger writing and validation. Use for new or resumed imports in statements/raw/ and statements/import-status.yml.
---

Read [common guidance](../../references/common.md) once and the [import contract](../../references/import-review.md) sections needed for field meanings and status. The panel supplements conversation summaries. Import owns orchestration and status; the parsed transactions are the write input.

## Select and process

Create one session JSON for the conversation with explicit raw/parsed membership, initialize each parsed document before extraction, and open its review panel. Use ordinary file edits and the bundled schemas/examples. Preserve completed imports and their artifacts. Route required structural status migration to `$auto-bean:auto-bean-migrate`.

Inspect Git state, fingerprint selected PDF/CSV/XLSX/XLS sources and select matching indexed source hints. Assign each source to `$auto-bean:auto-bean-process` with the [shared ownership context](../../references/common.md#ownership). Accept only its documented status proposals. Broker inline input; a saved answer/correction is not approval or a resolved blocker. Never release partial/untrustworthy extraction downstream.

Only Import edits the lifecycle status YAML. Keep source facts and decisions in parsed JSON, membership/prices in the session, and operational pointers/flags in YAML. Do not introduce separate stage documents or copy transactions into the session.

## Accounts and balances

Use `$auto-bean:auto-bean-query` to classify each account as mapped, first-seen or blocked. Publish mappings, rationale and proposed required directives in account review without changing extracted names/balances. Unresolved identity, currency, dates or mapping needs `state: needs_input` and supported suggestions.

Compare beginning-of-day openings with existing ledger evidence. A first-seen account may need a minimal opening directive and a source-supported opening transaction; present these with the transaction review before writing. An unexplained balance difference is a blocker, never permission to invent an adjustment.

Propose one document directive per mapped account, dated to statement period end, with a safe path to raw evidence; deduplicate date/account/path. Transaction exports without periods need an explicitly supported date. Record query dates, provenance and differences; mark missing balances unavailable. Resolved work reaches `categorize_ready`.

## Categorization and shared transactions

Invoke `$auto-bean:auto-bean-categorize` on complete evidence. Resolve inline input and use Query to compare transfers/duplicates with supplied session rows and accepted ledger history. Compare amount/currency, timing, references, fees/FX and ownership. Never silently net, drop or deduplicate uncertain records.

Every row needs a disposition. A paired transfer has reciprocal links, one posting owner and one economic ledger transaction retaining both source identities. Hold unresolved dependencies. Only complete reviewed decisions reach `write_ready`.

## Review, write and validate

Run the shared validation command with `--session <id> --stage review` after decisions are ready. Resolve errors, then present the current parsed mappings, explicit postings and required supporting directives in conversation and the panel. When first entering `final_review`, the ledger is unchanged. That status remains until writing and validation finish, so an interrupted approved write may already contain some entries; inspect provenance before resuming. Obtain explicit approval of the current review in conversation or the panel. Keep chat approval in the conversation; do not create approval JSON. Material corrections require renewed approval.

Invoke `$auto-bean:auto-bean-write` after approval to edit the ledger directly from these parsed decisions. Write checks existing source IDs before appending and returns changed files or concrete blockers. A shared transfer requires all affected statement approvals and is written once.

Run [shared validation](../../references/common.md#validation) with `--session <id> --stage written`. It checks every source row and reviewed posting, duplicate/transfer handling, ledger validity and available closing balances at the correct dates. Only a current passed written result permits Import to edit YAML to `done`. Interrupted writes or validation failures remain incomplete; resume by inspecting actual provenance, never by appending everything again.

Invoke `$auto-bean:auto-bean-prices` once after statement decisions and resume its follow-ups. Prices have separate approval and do not reverse completed statements. No required commodity means a structured zero-job `no_op`.

Invoke `$auto-bean:auto-bean-memory` after successful ledger validation. It derives eligible learning from accepted decisions, approval and actual ledger evidence, then compares governed memory. Report actual writes, no eligible work or blockers in conversation. Before completion, check YAML/document agreement, current validation, price results and outstanding input.

## Final status block

End every user-facing import response with this block and no text afterward:

```markdown
---

## Import Status: <label>

**Summary:** <concise outcome with counts/paths when useful.>
**Next Step:** <one user action, or "None." when Complete.>
```

Use `Needs Your Input` for unresolved choices; `Ready For Review` for pending approval; `Ready To Write` for approved unwritten transactions; `Validation Failed` for required repair; `Complete` only when all in-scope statements are done with no price/follow-up approval pending; or `No Changes Made` when no eligible work or state change occurred.
