---
name: auto-bean-write
description: Draft, review, and safely write Beancount transactions into the ledger from trusted evidence. Use when a Coding agent needs to add or update transaction entries in `ledger.beancount` or included `beancount/**` files, choose accounts and postings, respect Beancount balancing and account currency constraints, or ask and wait for clarification when transaction intent is ambiguous.
---

Always read before acting:

- `.agents/skills/shared/workflow-rules.md`
- `.agents/skills/shared/beancount-syntax-and-best-practices.md`

Read when needed:

- `.agents/skills/shared/memory-access-rules.md` when transaction evidence includes memory-derived suggestions or when an approved transaction-writing result reveals reusable memory, so any persistence is handed to `$auto-bean-memory`
- `.agents/skills/shared/question-handling-contract.md` before asking, returning, or resuming transaction-specific clarification questions


If the transaction-writing task is part of an import workflow, make sure to:

- read `.agents/skills/shared/parsed-statement-jq-reading.md` before inspecting large parsed statement JSON files
- have the path to the relevant parsed statement in `statements/parsed/` with its process artifact under `.auto-bean/artifacts/process/`
- have the path to the relevant categorize artifact under `.auto-bean/artifacts/categorize/`
- have the path to the relevant import-owned artifact under `.auto-bean/artifacts/import/`

If the transaction-writing task is part of an import workflow but you don't have the relevant parsed statement, process artifact, categorize artifact, or import-owned artifact, stop and report the missing context instead of proceeding with assumptions.

Follow this workflow:

1. Restate the requested ledger-writing task in plain language.
2. Inspect the current ledger context before drafting anything:
   - read `ledger.beancount`
   - inspect included `beancount/**` files that are relevant to the target accounts or target date range
   - find existing `open` directives, recent similar transactions, account naming conventions, tags, links, metadata keys, and file placement patterns
3. Identify the evidence source that justifies the transaction:
   - reviewed `statements/parsed/*.json`
   - an existing ledger correction request
   - explicit user-provided transaction facts
   - another bounded workspace artifact with concrete transaction details
   - memory-derived suggestions handed off by `$auto-bean-import` from `$auto-bean-categorize`, with current evidence and attribution already attached
   - follow the shared memory access rules before using memory-derived suggestions
4. If the evidence does not establish the core transaction facts, follow the shared question-handling contract for the missing fields:
   - date
   - payee or narration shape when materially needed by the ledger style
   - posting accounts
   - amount and currency
   - transfer intent, duplicate risk, or balancing rationale
5. Check Beancount rules before encoding the entry:
   - transactions must balance
   - the header shape is dated transaction header plus postings
   - tags and links belong on the transaction header
   - metadata belongs on indented `key: value` lines under the entry or posting it describes
   - prefer explicit posting amounts even though Beancount can infer one omitted amount
   - respect currency constraints declared on `open` directives
   - when syntax, balancing behavior, metadata placement, or `open` directive constraints are unclear, consult Beancount documentation through Context7 before encoding an authoritative assumption
6. Choose the narrowest mutation target that fits the ledger's current include graph and organization.
   - reuse the file that already owns similar transactions when possible
   - do not reshuffle the include graph just to insert one transaction
7. Draft the transaction directly in the working tree using explicit, inspectable postings.
   - keep the transaction minimal
   - preserve the ledger's existing style for payee, narration, posting order, metadata, tags, links, indentation, and quoting
   - omit at most one posting amount, and only when the balancing intent is obvious from the evidence and ledger context
8. Run transaction-specific review checks on the drafted result:
   - compare against nearby ledger entries for likely duplicates
   - inspect same-date and same-amount activity for possible transfers
   - verify each posting account is already open for the relevant currency, or ask and wait before introducing supporting directives
   - check that no posting silently changes the economic meaning of the evidence
9. Ask a bounded clarification question instead of guessing whenever the evidence leaves any material ambiguity, following the shared question-handling contract:
   - account identity
   - transfer versus expense or income interpretation
   - duplicate suspicion
   - missing currency
   - missing counterposting
   - unclear payee, narration, or metadata needed to match ledger conventions
   - when invoked by `$auto-bean-import`, follow the shared import-invoked broker rule and return the pending-question id, artifact path, blocker flags, and safe work completed
   - otherwise wait for the user answer, then resume the same transaction-writing task rather than returning a terminal blocked state
   - if the answer is still ambiguous, follow the shared follow-up rule before proceeding or reporting the remaining blocker to the calling skill
10. Validate after drafting the mutation.
    - prefer `./scripts/validate-ledger.sh`
    - otherwise use `./.venv/bin/bean-check ledger.beancount`
    - if validation fails, do not claim success or finalize
    - leave the working-tree edit in place unless the user explicitly asks to revert it, and report the changed files, validation command, concrete failure, and smallest proposed fix
11. Present a concise review package before any commit or push step:
    - what transaction was written or changed
    - which file changed and why it is the right target
    - the evidence used
    - any assumptions that remained after evidence review
    - duplicate, transfer, balancing, or currency risks found
    - the validation outcome
    - a clear statement that the working tree is changed but not finalized until approval is granted
12. Ask for explicit approval before commit or push finalization when used directly. When invoked by `$auto-bean-import`, never own commit or push finalization; return the mutation, validation, focused diff summary, assumptions, blockers, pending-question ids, and import artifact path using the shared compact return schema for orchestrator-owned approval and finalization. If approval is denied or deferred, leave the working-tree mutation unfinalized and explain its current state.

Guardrails:

- Keep the scope limited to writing or correcting transaction entries and the minimum supporting directives required for those entries.
- Do not silently invent accounts, currencies, payees, links, or metadata.
- Do not silently net transactions together, merge duplicates, or suppress suspected transfers.
- Do not rely on an omitted posting amount when the counterposting account or balance intent is still uncertain.
- Do not write into an account that is closed or restricted to different currencies by its `open` directive.
- Do not bypass validation or the commit/push approval boundary; when import-invoked, that boundary is owned by `$auto-bean-import`.
- Do not imply that a drafted transaction is accepted history before explicit approval and successful finalization.
