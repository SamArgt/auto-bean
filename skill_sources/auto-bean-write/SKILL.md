---
name: auto-bean-write
description: Draft, review, and safely write Beancount transactions into the ledger from trusted evidence. Use when a Coding agent needs to add or update transaction entries in `ledger.beancount` or included `beancount/**` files, choose accounts and postings, respect Beancount balancing and account currency constraints, or ask and wait for clarification when transaction intent is ambiguous.
---

Read these references before acting:

- `.agents/skills/shared/beancount-syntax-and-best-practices.md`
- `.agents/skills/shared/memory-access-rules.md` when transaction evidence includes memory-derived suggestions or when an approved transaction-writing result reveals reusable memory, so any persistence is handed to `$auto-bean-memory`

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
   - this skill verifies ledger context and does not independently treat governed memory as authority
4. If the evidence does not establish the core transaction facts, ask a bounded clarification question, wait for the answer, then resume drafting with that answer in context. When invoked by `$auto-bean-import`, return the question and blocker details to that calling stage instead of asking directly, so `$auto-bean-import` can keep the main import thread and batch user input:
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
9. Ask a bounded clarification question instead of guessing whenever the evidence leaves any material ambiguity. When invoked by `$auto-bean-import`, return the pending question to the caller after reporting any safe draft/review work already completed; otherwise wait for the user answer, then resume the same transaction-writing task rather than returning a terminal blocked state:
   - account identity
   - transfer versus expense or income interpretation
   - duplicate suspicion
   - missing currency
   - missing counterposting
   - unclear payee, narration, or metadata needed to match ledger conventions
   - if the answer is still ambiguous, ask one bounded follow-up and wait again before proceeding or reporting the remaining blocker to the calling skill
10. Validate after drafting the mutation.
    - prefer `./scripts/validate-ledger.sh`
    - otherwise use `./.venv/bin/bean-check ledger.beancount`
    - if validation fails, stop before any success claim and explain the concrete failure
11. Present a concise review package before any commit or push step:
    - what transaction was written or changed
    - which file changed and why it is the right target
    - the evidence used
    - any assumptions that remained after evidence review
    - duplicate, transfer, balancing, or currency risks found
    - the validation outcome
    - a `git diff -- <paths>` view or equivalent focused diff summary
    - a clear statement that the working tree is changed but not finalized until approval is granted
12. Ask for explicit approval before commit or push finalization. If approval is denied or deferred, leave the working-tree mutation unfinalized and explain its current state.

Guardrails:

- Keep the scope limited to writing or correcting transaction entries and the minimum supporting directives required for those entries.
- Do not silently invent accounts, currencies, payees, links, or metadata.
- Do not silently net transactions together, merge duplicates, or suppress suspected transfers.
- Do not rely on an omitted posting amount when the counterposting account or balance intent is still uncertain.
- Do not write into an account that is closed or restricted to different currencies by its `open` directive.
- Do not bypass validation or the commit/push approval boundary.
- Do not imply that a drafted transaction is accepted history before explicit approval and successful finalization.
