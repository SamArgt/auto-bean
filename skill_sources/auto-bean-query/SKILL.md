---
name: auto-bean-query
description: Query and explain Beancount ledgers safely with `bean-query` and the Beancount Query Language (BQL). Use when Codex needs to answer ledger-analysis questions such as balances, account activity, date-bounded totals, register views, account discovery, or transaction inspection from `ledger.beancount` and included `beancount/**` files without mutating the ledger.
---

# Auto Bean Query

Read these references before acting:

- `.agents/skills/auto-bean-query/references/bean-query-patterns.md`
- `.agents/skills/shared/beancount-syntax-and-best-practices.md` when account hierarchy, directive names, currency restrictions, or other ledger semantics matter for interpreting results
- `.agents/skills/shared/memory-access-rules.md` when query results might inform reusable memory or may help verify advisory memory reuse against ledger facts, so any persistence is handed to `$auto-bean-memory`

Follow this workflow:

1. Restate the user's question as a ledger-analysis task.
   - Translate vague requests like "what changed in checking last month?" into concrete outputs such as balances, postings, dates, payees, or grouped totals.
   - Confirm the query target implicitly from the workspace layout: prefer `ledger.beancount` as the root ledger unless the workspace clearly uses another root file.
2. Inspect the current workspace before querying.
   - Read the root ledger file and any obvious include targets needed to understand account names, root account options, or whether the ledger uses unusual structure.
   - Reuse the workspace's existing account names and hierarchy rather than inventing aliases.
3. Read `.agents/skills/auto-bean-query/references/bean-query-patterns.md` for common query shapes and result-interpretation guidance.
4. Use Context7 Beancount docs before making non-trivial assumptions about `bean-query`, BQL syntax, aggregation behavior, inventory math, or date-window semantics.
   - Prefer `/beancount/docs`.
   - Treat Beancount documentation as the authority for query syntax and reporting semantics.
5. Choose the narrowest query that answers the user safely.
   - Prefer direct CLI execution: `bean-query ledger.beancount 'SELECT ...'`
   - Use filters for account patterns, date bounds, or explicit accounts instead of broad full-ledger dumps.
   - Prefer grouped summaries first for exploratory questions, then drill into register-style detail if needed.
6. Use Beancount-native query patterns rather than inventing SQL features that BQL may not support.
   - For balances by account, prefer `SELECT account, sum(position) ... GROUP BY account`.
   - For readable commodity breakdowns, prefer `units(sum(position))` and `cost(sum(position))` when inventories would otherwise be opaque.
   - For register-style output, prefer `SELECT date, payee, narration, account, position, balance ... ORDER BY date`.
   - For period reports, use `FROM OPEN ON ... CLOSE ON ...` semantics when the question is about reporting windows rather than raw posting dates.
7. Execute the query, inspect the raw result, and sanity-check it before answering.
   - If the result is empty, explain whether that likely means no matching postings, a too-narrow filter, or an account-name mismatch.
   - If the result mixes multiple commodities or lots, explain that `position` and `balance` may be inventories rather than single scalar amounts.
   - If market value conversion or cost basis would materially change the answer, say so explicitly instead of implying a simple cash balance.
8. Present the outcome in an audit-friendly way.
   - Show the actual `bean-query` command or the final BQL query.
   - Summarize what the result means in plain language.
   - Call out important caveats such as inventory aggregation, account-pattern assumptions, empty-result ambiguity, or date-window semantics.
   - Offer a narrower follow-up query when the user wants to drill down.
9. Preserve boundaries.
   - Do not mutate `ledger.beancount`, `beancount/**`, or other workspace files in this skill.
   - Do not write `.auto-bean/memory/**`; if an approved query outcome should become reusable learning, hand it to `$auto-bean-memory`.
   - Do not add Beancount `query` directives or saved reports unless the user explicitly asks for a ledger edit.
   - If the user wants to change the ledger rather than inspect it, hand off to the structural mutation workflow instead of expanding this skill's scope.

Guardrails:

- Keep this skill read-only.
- Prefer `bean-query` over ad hoc parsing when the question is answerable in BQL.
- Fail closed when account identity, date interpretation, or valuation semantics are ambiguous.
- Do not overstate precision when results depend on inventories, costs, or price data the query did not normalize.
- Keep outputs concise, inspectable, and easy to reconcile against the ledger.
