---
name: auto-bean-import
description: Import new statements from statements/raw/ or resume unfinished groups in statements/import-status.yml through review, writing and validation.
---

Import owns orchestration/status; parsed decisions are the write input. Read [common guidance](../../references/common.md) once. The [contract](../../references/import-review.md) supplies field meanings, schemas and diagrams. The panel supplements conversation.

## Select and process

1. Inspect `statements/import-status.yml` and its saved sessions for unfinished groups first. Resume unfinished groups at their saved stages with existing session/group IDs and parsed files. Preserve decisions, answers and completed evidence. Skip done groups unless rework is requested. Use ordinary file edits; route structural status migration to `$auto-bean:auto-bean-migrate`.
2. If no unfinished groups remain, scan `statements/raw/` with Git status and tracked/untracked file listings for new PDF/CSV/XLSX/XLS statements. Exclude completed imports using saved status. With no new sources, report no changes; create no empty session.
3. Group new sources before creating session JSON per the [session schema](../../references/schemas/session.schema.json). Honor user groups; otherwise default to one statement per group, grouping related sources when shared processing or reconciliation helps. Summarize groups. Each source belongs to one group, with one parsed JSON and one YAML lifecycle entry. Preserve resumed grouping unless the user changes it or evidence warrants an explained revision.
4. Save new groups with workspace-unique `group_id`, `name`, `origin` (`user` or `agent`), `source_files` and `parsed_group`. Set YAML `groups.<group_id>` fields: `session_id`, `parsed_group`, `current_status` and `sources` keyed by raw path. Keep per-source fingerprints and retry counts. Validate session/status membership and open the review panel before dispatch, including on resume.
5. Inspect Git state, fingerprint selected sources and select matching indexed hints. Spawn a processing subagent per group needing extraction. Have it use `$auto-bean:auto-bean-process` for each source and create group parsed JSON before extraction. Supply members, session, fingerprints, parsed target, retry state, hints and [ownership context](../../references/common.md#ownership). Accept its group status proposal and per-source outcomes. Never release partial or untrustworthy extraction downstream.

Only Import edits lifecycle YAML, using the [status schema](../../references/schemas/status.schema.json). Keep source facts and decisions in the group's parsed `statements` list, membership/groups/prices in the session, and operational pointers/flags in YAML. Do not create per-source lifecycle entries, separate stage documents or transaction copies in the session.

Use separate processing and categorization workers, even for one-statement groups. Run independent groups in parallel within capacity; queue others. Reuse each stage worker for follow-ups where available. Never run both stages on the same parsed document at once. Broker inline input and continue independent safe work while holding affected statements and linked transfers. A saved answer/correction is neither approval nor a resolved blocker. Ask for input to resolve ambiguity, not for mandatory approval at each stage.

## Accounts and balances

Use `$auto-bean:auto-bean-query` to classify accounts as mapped, first-seen or blocked. Publish mappings, rationale and required proposed directives in account review per the [parsed schema](../../references/schemas/parsed-v2.schema.json). Preserve extracted names/balances. Unresolved identity, currency, dates or mapping needs `state: needs_input` and supported suggestions.

Compare beginning-of-day openings with ledger evidence. A first-seen account may need a minimal opening directive and source-supported opening transaction; include them in the transaction review. Unexplained differences block progress; never invent adjustments.

Propose one document directive per mapped account, dated to statement period end, with a safe raw-evidence path. Deduplicate date/account/path. Exports without periods need an explicitly supported date. Record query dates, provenance and differences; mark missing balances unavailable. Resolved work reaches `categorize_ready`.

## Categorization and shared transactions

Spawn a categorization subagent for each `categorize_ready` group or ready members explicitly released by Import. Have it use `$auto-bean:auto-bean-categorize`. Supply membership, complete ready evidence, group status, session, answers and relevant reconciliation rows from other groups. Hold blocked members and resume them with this worker when ready. Require per-source findings and one group status proposal.

Import resolves shared decisions and inline input across groups. Use Query to compare transfers/duplicates against session rows and accepted ledger history. Compare amount/currency, timing, references, fees/FX and ownership. Never silently net, drop or deduplicate uncertain records.

Give every row a disposition. Paired transfers need reciprocal links, one posting owner and one transaction retaining both source identities. Hold unresolved dependencies. Only complete reviewed decisions reach `write_ready`.

## Review, write and validate

Mappings, postings and supporting directives form one statement review. Resolved account, opening-balance and category decisions need no separate approval rounds.

Run shared validation with `--session <id> --stage review`. Resolve errors, then present current mappings, explicit postings and supporting directives in conversation and the panel. The ledger is unchanged on first entry to `final_review`. Obtain explicit approval of that review in conversation or the panel. Keep chat approval in conversation; do not create approval JSON. Material corrections require renewed approval.

After approval, invoke `$auto-bean:auto-bean-write` to write directly from parsed decisions. Write checks existing source IDs before appending and returns changed files or blockers. A shared transfer needs all affected statement approvals and is written once.

Keep partial/interrupted writes at `final_review` or `write_blocked`. Preserve completed evidence and inspect provenance before resuming; approved entries may exist. Mark a group `done` only when every member has current passed `written` validation and no unresolved group flags. Revalidate when source evidence, decisions or ledger files change. Follow [per-result validation rules](../../references/common.md#validation) when other members remain pending. Interrupted writes and affected validation failures remain incomplete.

## Prices and Memory

Invoke `$auto-bean:auto-bean-prices` once after the current statement pass, even when other statements remain pending; resume its follow-ups. New price directives need separate approval and do not reverse completed groups. No required commodity means a structured zero-job `no_op`.

Finish the pass by invoking `$auto-bean:auto-bean-memory` once with workspace, session/parsed paths and approval context. Have it read the [Memory skill](../auto-bean-memory/SKILL.md) and artifacts, then update relevant memory. Apply returned `MEMORY.md` edits under its main-thread rules. Summarize the outcome.

## Final status block

End every user-facing import response with this block and no text afterward:

```markdown
---

## Import Status: <label>

**Summary:** <outcome with useful counts/paths.>
**Next Step:** <one user action, or "None." when Complete.>
```

Use `Needs Your Input` for unresolved choices; `Ready For Review` for pending approval; `Ready To Write` for approved unwritten transactions; `Validation Failed` for required repair; `Complete` only when all in-scope groups are done with no price/follow-up approval pending; or `No Changes Made` when no eligible work or state change occurred.
