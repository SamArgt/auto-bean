---
name: auto-bean-import
description: Import statements from discovery through extraction, account mapping, categorization, user review, ledger writing and validation. Use for new or resumed imports in statements/raw/ and statements/import-status.yml.
---

Read [common guidance](../../references/common.md) once and the [import contract](../../references/import-review.md) sections needed for field meanings and status. The panel supplements conversation summaries. Import owns orchestration and status; the parsed transactions are the write input.

For the end-to-end overview, including human-input loops and parallel work, see the [process flow](../../references/import-review.md#process-flow).

## Select and process

Create one session JSON for a new import conversation using the [session schema](../../references/schemas/session.schema.json), or reuse its existing session on resume. Select raw sources and groups. Process creates each group's parsed JSON before extraction. Resume unfinished groups from their saved status and source sections, preserving decisions and answers. Skip completed groups unless the user requests rework. Use ordinary file edits. Route required structural status migration to `$auto-bean:auto-bean-migrate`.

Organize each session into statement groups. Use the user's explicit groups; otherwise infer groups from the sources and task context. Default to one statement per group. Group related statements when they benefit from shared processing or reconciliation context. Persist each group in session `groups` with a stable `group_id`, a `name`, `origin` (`user` or `agent`), `source_files` and one `parsed_group` path. Summarize the groups in conversation. Each selected statement belongs to exactly one group. Preserve saved grouping and IDs on resume unless the user changes them or new evidence requires an explained revision. Each group owns one parsed JSON and one YAML status entry. Its parsed `statements` list keeps source-specific facts, inline decisions and approvals together; do not create per-statement parsed files or lifecycle entries.

Create or update `import-status.yml` under `groups.<group_id>` with `session_id`, `parsed_group`, `current_status` and `sources` keyed by raw path. Keep fingerprints and retry counts under those source entries. Group IDs must be unique in the workspace. Validate matching session/status membership, then open the review panel before dispatch.

Inspect Git state, fingerprint selected PDF/CSV/XLSX/XLS sources and select matching indexed source hints. For each group that needs processing, spawn a dedicated subagent and instruct it to use `$auto-bean:auto-bean-process` for every assigned source. Supply the group members, session, per-source fingerprints, the shared parsed target, retry state and matching hints with the [shared ownership context](../../references/common.md#ownership). Accept only its documented group status proposals and per-source outcomes. Broker inline input; a saved answer/correction is not approval or a resolved blocker. Never release partial/untrustworthy extraction downstream.

Only Import edits the lifecycle status YAML, following the [status schema](../../references/schemas/status.schema.json). Keep source facts and decisions in parsed JSON, membership/groups/prices in the session, and operational pointers/flags in YAML. Do not introduce separate stage documents or copy transactions into the session.

Spawn separate subagents for processing and categorization, including single-statement groups. Run independent groups in parallel within available capacity; queue remaining groups. Reuse the group's stage subagent for follow-up work where available. Do not run both stages on the same parsed document at once. Continue independent safe work while questions are pending; hold affected statements and linked transfers. Human-input loops resolve actual ambiguity, not mandatory approvals at every stage.

## Accounts and balances

Use `$auto-bean:auto-bean-query` to classify each account as mapped, first-seen or blocked. Publish mappings, rationale and proposed required directives in account review according to the [parsed schema](../../references/schemas/parsed-v2.schema.json), without changing extracted names/balances. Unresolved identity, currency, dates or mapping needs `state: needs_input` and supported suggestions.

Compare beginning-of-day openings with existing ledger evidence. A first-seen account may need a minimal opening directive and a source-supported opening transaction; present these with the transaction review before writing. An unexplained balance difference is a blocker, never permission to invent an adjustment.

Propose one document directive per mapped account, dated to statement period end, with a safe path to raw evidence; deduplicate date/account/path. Transaction exports without periods need an explicitly supported date. Record query dates, provenance and differences; mark missing balances unavailable. Resolved work reaches `categorize_ready`.

## Categorization and shared transactions

For each group at `categorize_ready`, or with ready members explicitly released by Import, spawn a dedicated categorization subagent and instruct it to use `$auto-bean:auto-bean-categorize`. Supply the group membership, complete ready evidence, the current group status entry, session, answers and relevant reconciliation rows from other groups. Hold blocked members and resume them with this stage subagent when ready. Require per-source findings and one group status proposal. Import resolves shared decisions across groups. Resolve inline input and use Query to compare transfers/duplicates with supplied session rows and accepted ledger history. Compare amount/currency, timing, references, fees/FX and ownership. Never silently net, drop or deduplicate uncertain records.

Every row needs a disposition. A paired transfer has reciprocal links, one posting owner and one economic ledger transaction retaining both source identities. Hold unresolved dependencies. Only complete reviewed decisions reach `write_ready`.

## Review, write and validate

Mappings, postings and required supporting directives form one statement review. Resolved account, opening-balance and category decisions do not require separate approval rounds.

Run the shared validation command with `--session <id> --stage review` after decisions are ready. Resolve errors, then present the current parsed mappings, explicit postings and required supporting directives in conversation and the panel. When first entering `final_review`, the ledger is unchanged. That status remains until writing and validation finish, so an interrupted approved write may already contain some entries; inspect provenance before resuming. Obtain explicit approval of the current review in conversation or the panel. Keep chat approval in the conversation; do not create approval JSON. Material corrections require renewed approval.

Invoke `$auto-bean:auto-bean-write` after approval to edit the ledger directly from these parsed decisions. Write checks existing source IDs before appending and returns changed files or concrete blockers. A shared transfer requires all affected statement approvals and is written once.

Mark a group `done` only when every member has current passed `written` validation and no unresolved group flags. An interrupted or partially written group remains `final_review` or `write_blocked`; preserve completed member evidence and inspect provenance before resuming. Revalidate when relevant source evidence, decisions or ledger files change. Follow the [per-result validation rules](../../references/common.md#validation) when other session members remain pending. Interrupted writes or affected validation failures remain incomplete; resume from actual provenance.

Invoke `$auto-bean:auto-bean-prices` once after the current statement pass, even if other statements remain pending, and resume its follow-ups. New price directives have separate approval and do not reverse completed groups. No required commodity means a structured zero-job `no_op`.

## Finish with Memory

At the end of the import pass, invoke `$auto-bean:auto-bean-memory` once with the workspace, session/parsed JSON paths and relevant approval context. Instruct it to read the [Memory skill](../auto-bean-memory/SKILL.md) alongside those artifacts and make the relevant memory updates. Include the outcome in the final summary; apply any returned `MEMORY.md` edit under that skill's main-thread rules.

## Final status block

End every user-facing import response with this block and no text afterward:

```markdown
---

## Import Status: <label>

**Summary:** <concise outcome with counts/paths when useful.>
**Next Step:** <one user action, or "None." when Complete.>
```

Use `Needs Your Input` for unresolved choices; `Ready For Review` for pending approval; `Ready To Write` for approved unwritten transactions; `Validation Failed` for required repair; `Complete` only when all in-scope groups are done with no price/follow-up approval pending; or `No Changes Made` when no eligible work or state change occurred.
