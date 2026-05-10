---
name: auto-bean-write
description: Draft, review, and safely write Beancount transactions into the ledger from trusted evidence. Use when a Coding agent needs to add or update transaction entries in `ledger.beancount` or included `beancount/**` files, choose accounts and postings, respect Beancount balancing and account currency constraints, or ask and wait for clarification when transaction intent is ambiguous.
---

MUST read before acting:

- `.auto-bean/memory/MEMORY.md`
- `.agents/skills/shared/workflow-rules.md`
- `.agents/skills/shared/beancount-syntax-and-best-practices.md`

Read when needed:

- `.agents/skills/shared/memory-access-rules.md` MUST be read when transaction evidence includes memory-derived account, category, transfer, duplicate, source, or posting suggestions; when current evidence contradicts a memory-derived suggestion; or when an approved transaction-writing result reveals reusable memory.
- `.agents/skills/shared/parsed-statement-jq-reading.md` MUST be read before inspecting any parsed statement JSON from an import handoff, before selecting transaction rows from a large parsed file, and before troubleshooting mismatches between parsed `account_id` values and posting evidence.


If the transaction-writing task is part of an import workflow, make sure to:

- read `.agents/skills/shared/parsed-statement-jq-reading.md` before inspecting large parsed statement JSON files
- have the path to the relevant parsed statement in `statements/parsed/` with its process artifact under `.auto-bean/artifacts/process/`
- have the path to the relevant categorize artifact under `.auto-bean/artifacts/categorize/`
- have the path to the relevant import-owned artifact under `.auto-bean/artifacts/import/`

If the transaction-writing task is part of an import workflow but you don't have the relevant parsed statement, process artifact, categorize artifact, or import-owned artifact, stop and report the missing context instead of proceeding with assumptions.

Follow this workflow:

1. Restate the requested ledger-writing task and whether it is direct or import-invoked.
2. Inspect the current ledger context before drafting anything:
   - read `ledger.beancount`
   - inspect included `beancount/**` files that are relevant to the target accounts or target date range
   - find existing `open` directives, recent similar transactions, account naming conventions, tags, links, metadata keys, and file placement patterns
3. Identify the evidence source that justifies the transaction:
   - reviewed the parsed statement under `statements/parsed/`
   - an existing ledger correction request
   - explicit user-provided transaction facts
   - another bounded workspace artifact with concrete transaction details
   - memory-derived suggestions handed off by `$auto-bean-import` from `$auto-bean-categorize`, with current evidence and attribution already attached
   - follow the shared memory access rules before using memory-derived suggestions
   - use `.auto-bean/memory/MEMORY.md` for relevant user profile, main-account, preference, and correction context, but do not let it override transaction evidence
4. If the evidence does not establish the core transaction facts, follow the shared question-handling rules for the missing fields:
   - date
   - payee or narration shape
   - posting accounts
   - amount and currency
   - transfer intent, duplicate risk, or balancing rationale
5. Check Beancount rules before encoding the entry:
   - transactions must balance
   - header data must contain the payee and narration and avoid generic payees such as "April shopping online" when the statement provides clearer details, but do not guess when the statement is ambiguous
   - metadata belongs on indented `key: value` lines under the entry or posting it describes
   - include `source` and `record_id` in the metadata
   - prefer explicit posting amounts even though Beancount can infer one omitted amount
   - respect currency constraints declared on `open` directives
   - when syntax, balancing behavior, metadata placement, or `open` directive constraints are unclear, consult Beancount documentation through Context7 before encoding an authoritative assumption
6. Choose the narrowest mutation target that fits the ledger's current include graph and organization.
   - reuse the file that already owns similar transactions when possible
   - do not reshuffle the include graph just to insert one transaction
   - default-allowed supporting directives are limited to transaction entries, minimal `open` directives required for the target accounts, and narrowly scoped `balance` directives required for integrity or validation of the written transaction
   - ask for explicit user approval before writing anything beyond that allowlist, including include-graph reorganization, new include files, broad account-tree moves, commodity declarations, price directives, plugin/options changes, or unrelated cleanup
7. Draft the transaction directly in the working tree using explicit, inspectable postings.
   - keep the transaction minimal but never group entries, write the postings at the vendor-level.
8. Ask a bounded clarification question instead of guessing whenever the evidence leaves any material ambiguity, following the shared question-handling rules:
   - when invoked by `$auto-bean-import`, follow the shared import-invoked broker rule and return the pending-question id, artifact path, blocker flags, and safe work completed
   - otherwise wait for the user answer, then resume the same transaction-writing task rather than returning a terminal blocked state
9. Validate after drafting the mutation.
    - prefer `./scripts/validate-ledger.sh`
    - otherwise use `./.venv/bin/bean-check ledger.beancount`
    - if validation fails, do not claim success or finalize
    - leave the working-tree edit in place unless the user explicitly asks to revert it, and report the changed files, validation command, concrete failure, and smallest proposed fix
10. Present a concise review package before any commit or push step:
    - what transaction was written or changed
    - which file changed and why it is the right target
    - the evidence used
    - any assumptions that remained after evidence review
    - duplicate, transfer, balancing, or currency risks found
    - the validation outcome
    - a clear statement that the working tree is changed but not finalized until approval is granted
11. When invoked by `$auto-bean-import` use the shared compact return schema for orchestrator-owned approval and finalization.
Guardrails:

- Keep the scope limited to writing or correcting transaction entries and the minimum supporting directives required for those entries.
- Do not silently invent accounts, currencies, payees, links, or metadata.
- Do not silently net transactions together, merge duplicates, or suppress suspected transfers.
- Do not rely on an omitted posting amount when the counterposting account or balance intent is still uncertain.
- Do not write into an account that is closed or restricted to different currencies by its `open` directive.
- Do not imply that a drafted transaction is accepted history before explicit approval and successful finalization.
