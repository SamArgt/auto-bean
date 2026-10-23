---
name: auto-bean-import
description: Import new statements from statements/raw/ or resume unfinished groups in statements/import-status.yml through review, writing and validation.
---

Import owns orchestration/status; parsed decisions are the write input. Read [common guidance](../../references/common.md) once. The [contract](../../references/import-review.md) supplies field meanings, schemas and diagrams. The panel supplements conversation.

## Select and process

1. Inspect `statements/import-status.yml` and its saved sessions. Resume unfinished groups and unresolved price runs, approvals or follow-ups, even when all groups are `done`. Keep session/group IDs, parsed files, decisions, answers and completed evidence. Reopen done groups only for explicit rework. Route structural status migration to `$auto-bean:auto-bean-migrate`.
2. On every pass, scan `statements/raw/` with Git status and tracked/untracked listings for new PDF/CSV/XLSX/XLS sources. Exclude sources already assigned in saved status. New evidence may resolve a blocked group; unrelated sources may progress independently. Report no changes only when neither new sources nor unfinished session work remain; create no empty session.
3. Honor user groups; otherwise default to one statement per group and combine sources when shared processing helps. Add new groups needed for reconciliation to the active session so linked rows remain in one session. Preserve existing membership unless the user changes it or evidence warrants an explained revision. With multiple possible sessions, resolve the intended assignment. Summarize new or revised groups before dispatch.
4. Save membership using the [session](../../references/schemas/session.schema.json) and [status](../../references/schemas/status.schema.json) schemas: one workspace-unique group ID, one parsed path and one YAML lifecycle entry per group; each source belongs to one group. Keep per-source fingerprints and retry counts. Check session/status membership and open the review panel, including on resume. If unavailable, report that limitation and use conversation review.
5. Assign extraction to `$auto-bean:auto-bean-process`. Supply members, session, fingerprints, parsed target, retry state, matching source hints and [ownership context](../../references/common.md#ownership). Process creates the group JSON before extraction and returns per-source outcomes and one group status proposal. Release only complete, trustworthy source sections downstream.

Only Import edits lifecycle YAML, using the [status schema](../../references/schemas/status.schema.json). Keep source facts and decisions in the group's parsed `statements` list, membership/groups/prices in the session, and operational pointers/flags in YAML. Do not create per-source lifecycle entries, separate stage documents or transaction copies in the session.

Prefer separate processing and categorization workers for substantial work. For small groups or unavailable delegation, run their skills serially in the main thread with the same stage boundaries. Parallel workers use distinct group files; reuse them for follow-ups when available. Never run two stages on one parsed file at once. Broker input while independent work continues; hold affected members and linked transfers. Check saved answers before resolving blockers. Clarification does not grant approval or require a separate stage approval.

## Accounts and balances

Use `$auto-bean:auto-bean-query` to classify accounts as mapped, first-seen or blocked. Publish mappings, rationale and required proposed directives in account review per the [parsed schema](../../references/schemas/parsed-v2.schema.json). Preserve extracted names/balances. Unresolved identity, currency, dates or mapping needs `state: needs_input` and supported suggestions.

Compare beginning-of-day openings with ledger evidence. A first-seen account may need a minimal opening directive and source-supported opening transaction; include them in the transaction review. Unexplained differences block progress; never invent adjustments.

Propose one document directive per mapped account, dated to statement period end, with a safe raw-evidence path. Deduplicate date/account/path. Exports without periods need an explicitly supported date. Record query dates, provenance and differences; mark missing balances unavailable. Resolved work reaches `categorize_ready`.

## Categorization and shared transactions

Assign `$auto-bean:auto-bean-categorize` to each `categorize_ready` group or ready members explicitly released by Import. Supply membership, complete evidence, status, session, answers and reconciliation rows from other groups. Hold blocked members and resume the same stage when ready. Require per-source findings and one group status proposal.

Import resolves shared decisions and inline input across groups. Use Query to compare transfers/duplicates against session rows and accepted ledger history. Compare amount/currency, timing, references, fees/FX and ownership. Never silently net, drop or deduplicate uncertain records.

Give every row a disposition. Paired transfers need reciprocal links, one posting owner and one transaction retaining both source identities. Hold unresolved dependencies. Only complete reviewed decisions reach `write_ready`.

## Review, write and validate

Mappings, postings and supporting directives form one statement review. Resolved account, opening-balance and category decisions need no separate approval rounds.

Pause edits across the session and run shared validation with `--session <id> --stage review` under the [per-result rules](../../references/common.md#validation). Resolve affected errors; unrelated pending members need not block ready work. Present mappings, explicit postings and supporting directives in conversation and the available panel. The ledger is unchanged on first entry to `final_review`. Obtain explicit approval of that review. Keep chat approval in conversation; do not create approval JSON. Material corrections require renewed approval.

After approval, invoke `$auto-bean:auto-bean-write` to write directly from parsed decisions. Write checks existing source IDs before appending and returns changed files or blockers. A shared transfer needs all affected statement approvals and is written once.

Keep partial/interrupted writes at `final_review` or `write_blocked`. Preserve completed evidence and inspect provenance before resuming; approved entries may exist. Mark a group `done` only when every member has current passed `written` validation and no unresolved group flags. Revalidate when source evidence, decisions or ledger files change. Follow [per-result validation rules](../../references/common.md#validation) when other members remain pending. Interrupted writes and affected validation failures remain incomplete.

## Prices and Memory

Run or resume `$auto-bean:auto-bean-prices` after the statement pass, including a price-only resume. Reuse existing runs and resolve pending work before starting another fetch. Do not repeat an unchanged completed run. New directives need separate approval and do not reverse completed groups. No required commodity means a structured zero-job `no_op`.

Finish the pass with `$auto-bean:auto-bean-memory`, supplying workspace, session/parsed paths and approval context. It derives eligible lessons from the artifacts. Apply any returned workspace `MEMORY.md` edits under its main-thread rules and summarize the outcome.

## Final status block

End responses that hand control back to the user with this block. Omit it from progress updates and in-flight clarification questions.

```markdown
---

## Import Status: <label>

**Summary:** <outcome with useful counts/paths.>
**Next Step:** <one user action, or "None." when Complete.>
```

Use `Needs Your Input` for unresolved choices; `Ready For Review` for pending approval; `Ready To Write` for approved unwritten transactions; `Validation Failed` for required repair; `Complete` only when all in-scope groups are done with no price/follow-up approval pending; or `No Changes Made` when no eligible work or state change occurred.
