---
name: auto-bean-import
description: Import new statements or resume saved import sessions through review, writing and validation.
---

Import owns orchestration/status; parsed decisions drive writes. Read [guidance](../../references/common.md) and the [contract](../../references/import-review.md). The panel supplements chat.

## Select and process

On each pass, including resume, use Query for balances/history scoped by account, date or source ID. Avoid full dumps; reuse unchanged configuration/includes. Hashes do not replace content inspection.

1. Inspect `statements/import-status.yml` and saved sessions. Resume unfinished groups, price runs, approvals and follow-ups, even if all groups are `done`. Keep IDs, parsed files, decisions, answers and completed evidence. Reopen done groups only for explicit rework. Route structural status migration to `$auto-bean:auto-bean-migrate`.
2. Each pass, scan `statements/raw/` with Git status and tracked/untracked listings for new PDF/CSV/XLSX/XLS sources. Exclude assigned sources. New evidence may unblock a group; unrelated sources may progress independently. Report no changes only if no new sources or unfinished session work remain. Create no empty session.
3. Honor user groups; otherwise use one statement per group, combining sources when shared processing helps. Add reconciliation groups to the active session to keep linked rows together. Change membership only on user request or an explained evidence-based revision. Resolve ambiguous session assignments. Summarize new or revised groups before dispatch.
4. Save and check [session](../../references/schemas/session.schema.json) and [status](../../references/schemas/status.schema.json) membership: one workspace-unique group ID, parsed path and YAML lifecycle entry per group; one group per source. Keep source fingerprints and retry counts.
5. Assign extraction to `$auto-bean:auto-bean-process`. Supply members, session, fingerprints, parsed target, retry state, matching source hints and [ownership](../../references/common.md#ownership). Process creates group JSON before extraction and returns per-source outcomes and a group status proposal. Release only complete, trustworthy sources downstream.

Import owns lifecycle YAML; migration may add reviewed `legacy: true` to completed groups. Keep marked sources registered, skip review and report validation exclusions. Never reopen/reimport automatically. Store facts/decisions in parsed `statements`, membership/groups/prices in the session, and pointers/flags in YAML. No per-source lifecycle entries, stage documents or session transaction copies.

For substantial work, prefer separate processing and categorization workers; otherwise run their skills serially. Preserve stage boundaries. Parallel workers use distinct group files; reuse them for follow-ups. Start a downstream stage only after its file is released. Never run two stages on one parsed file at once. Hold affected members and linked transfers while independent work continues. Collect questions for the [consolidated handoff](#consolidated-handoff). Clarification is not approval and needs no stage approval.

## Accounts and balances

Use `$auto-bean:auto-bean-query` to classify accounts as mapped, first-seen or blocked. Save mappings, rationale and proposed directives in account review per the [statement schema](../../references/schemas/parsed-statement.schema.json) and [supporting-directive limits](../../references/import-review.md#transaction-dispositions). Preserve extracted names/balances. Unresolved identity, currency, dates or mapping needs `state: needs_input` and supported suggestions.

Compare beginning-of-day openings with ledger evidence. A first-seen account may need a minimal opening directive and source-supported opening transaction; include them in the transaction review. Unexplained differences block progress; never invent adjustments.

Propose one document directive per mapped account at period end, with a safe raw-evidence path. Deduplicate date/account/path. Exports without periods need a supported date. Record query dates, provenance and differences; mark missing balances unavailable. Resolved work reaches `categorize_ready`.

## Categorization and shared transactions

Assign `$auto-bean:auto-bean-categorize` to each `categorize_ready` group or ready members explicitly released by Import. Supply membership, complete evidence, status, session, answers and reconciliation rows from other groups. Hold blocked members and resume the same stage when ready. Require per-source findings and one group status proposal.

Import resolves shared decisions and inline input across groups. Use Query to compare transfers/duplicates against session rows and accepted ledger history. Compare amount/currency, timing, references, fees/FX and ownership. Never silently net, drop or deduplicate uncertain records.

Give every row a disposition. Paired transfers need reciprocal links, one posting owner and one transaction retaining both source identities. Hold unresolved dependencies. Only complete reviewed decisions reach `write_ready`.

## Consolidated handoff

Use one user handoff per preparation pass, including resume:

1. Collect questions in existing inline review fields and price-run records. Workers return completed work or persisted blockers without waiting for user answers. Finish independent work and runnable follow-ups, including cross-group transfer and duplicate checks. Before handoff, every dispatched worker must have returned or stopped at a persisted blocker, with no writes still running. A blocked worker counts as settled; an active worker does not.
2. Prepare available price follow-ups after statement preparation and before handoff, under [Prices and Memory](#prices-and-memory). Reread saved answers and have the owning stage apply them. Remove questions resolved by answers, ledger evidence or other statements. Complete any newly unblocked work before presenting the remaining questions.
3. Identify payment questions by source/account/record IDs and price questions by run/commodity IDs. Combine related rows only when one answer resolves them, such as a charge and reversal. Keep unresolved linked transfers held.
4. Run stable review validation and repair actionable errors under [Review, write and validate](#review-write-and-validate). Open the review panel once for this stable handoff. Present the consolidated question set or approval review once in chat, with the final status and next action. Do not duplicate the questions through both a question tool and the final response. Transaction and price approvals remain separate in scope.

Keep progress updates informational. Do not ask questions or open review during preparation unless the user explicitly requests an early view; label that view incomplete. On resume, consume saved answers before reopening review. Ask only remaining or newly discovered questions after dependent work settles. If the panel is unavailable, report it and give the same consolidated review in chat; do not repeatedly retry opening it during that pass. A later approval review after clarification is a new handoff, not approval implied by the answers.

## Review, write and validate

Review mappings, postings and supporting directives together. Resolved account, opening-balance and category decisions need no separate approval.

After runnable preparation settles, pause edits across the session and run shared validation with `--session <id> --stage review` under the [per-result rules](../../references/common.md#validation). Resolve affected errors; unrelated pending members need not block ready work. Present mappings, explicit postings and supporting directives at the consolidated handoff. The ledger is unchanged on first entry to `final_review`. Obtain explicit approval of that review. Keep chat approval in conversation; do not create approval JSON. Material corrections require renewed approval.

Before price preparation or statement writes, compare proposed commodities with prior ledger uses and operating currencies. A missing optional `commodity` directive alone does not make a commodity new. Save introduced commodities in the pending price run's `new_commodities` list. Pass it to Prices and preserve it on resume.

After approval, invoke `$auto-bean:auto-bean-write` to write directly from parsed decisions. Write checks existing source IDs before appending and returns changed files or blockers. A shared transfer needs all affected statement approvals and is written once.

Keep partial/interrupted writes at `final_review` or `write_blocked`. Preserve completed evidence and inspect provenance before resuming; approved entries may exist. Mark a group `done` only when every member has current passed `written` validation and no unresolved group flags. Revalidate when source evidence, decisions or ledger files change.

## Prices and Memory

Run or resume `$auto-bean:auto-bean-prices` after statement preparation and before the consolidated handoff, including price-only resumes. Supply proposed commodity evidence when statements are not yet written. Collect its questions and proposals for that handoff; resume approved writes afterward. Reuse existing runs; resolve pending work before another fetch. Do not repeat unchanged completed runs. Prices validates with `--price-run <id>` and the appropriate review or written stage to preserve pending statement reports. New directives need separate approval and do not reverse completed groups. No required commodity means a structured zero-job `no_op`; missing coverage does not.

Finish with `$auto-bean:auto-bean-memory`. Supply workspace, session/parsed paths and approval context. Apply its eligible workspace `MEMORY.md` edits under its main-thread rules and report the outcome.

## Final status block

End consolidated handoffs, including clarification requests, with this block. Omit it from progress updates.

```markdown
---

## Import Status: <label>

**Summary:** <outcome, counts/paths.>
**Next Step:** <one user action, or "None." when Complete.>
```

Use `Needs Your Input` for unresolved choices; `Ready For Review` for pending approval; `Ready To Write` for approved unwritten transactions; `Validation Failed` for required repair; `Complete` only when all in-scope groups are done with no price/follow-up approval pending; or `No Changes Made` when no eligible work or state change occurred.
