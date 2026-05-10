---
name: auto-bean-query
description: Query and explain Beancount ledgers safely with `bean-query` and the Beancount Query Language (BQL). Use when Codex needs to answer ledger-analysis questions such as balances, account activity, date-bounded totals, register views, account discovery, or transaction inspection from `ledger.beancount` and included `beancount/**` files without mutating the ledger.
---

# Auto Bean Query

MUST read before acting:
- `.auto-bean/memory/MEMORY.md`
- `.agents/skills/shared/workflow-rules.md`
- `.agents/skills/auto-bean-query/references/bean-query-patterns.md`

Read when needed:

- `.agents/skills/shared/beancount-syntax-and-best-practices.md` MUST be read before relying on account hierarchy, directive names, currency restrictions, `open`/`close` directives, or other ledger semantics to interpret results.
- `.agents/skills/shared/memory-access-rules.md` MUST be read when query results might inform reusable memory, when query results verify or contradict advisory memory, or when another skill asks this skill to check memory-derived facts against the ledger.

Follow this workflow:

1. Restate the user's question as a ledger-analysis task.
   - Translate vague requests like "what changed in checking last month?" into concrete outputs such as balances, postings, dates, payees, or grouped totals.
   - Confirm the query target implicitly from the workspace layout: prefer `ledger.beancount` as the root ledger unless the workspace clearly uses another root file.
2. Inspect the current workspace before querying.
   - Read the root ledger file and any obvious include targets needed to understand account names, root account options, or whether the ledger uses unusual structure.
   - Reuse the workspace's existing account names and hierarchy rather than inventing aliases.
3. Read `.agents/skills/auto-bean-query/references/bean-query-patterns.md` for common query shapes and result-interpretation guidance.
4. Use Context7 Beancount docs before making non-trivial assumptions about `bean-query`, BQL syntax, aggregation behavior, inventory math, or date-window semantics.
   - SHOULD prefer `/beancount/docs`.
   - Treat Beancount documentation as the authority for query syntax and reporting semantics.
5. Choose the narrowest query that answers the user safely.
   - SHOULD prefer direct CLI execution: `bean-query ledger.beancount 'SELECT ...'`
   - Use filters for account patterns, date bounds, or explicit accounts instead of broad full-ledger dumps.
   - SHOULD prefer grouped summaries first for exploratory questions, then drill into register-style detail if needed.
6. Use Beancount-native query patterns rather than inventing SQL features that BQL may not support.
   - For balances by account, prefer `SELECT account, sum(position) ... GROUP BY account`.
   - For readable commodity breakdowns, prefer `units(sum(position))` and `cost(sum(position))` when inventories would otherwise be opaque.
   - For register-style output, prefer `SELECT date, payee, narration, account, position, balance ... ORDER BY date`.
   - For period reports, use `FROM OPEN ON ... CLOSE ON ...` semantics when the question is about reporting windows rather than raw posting dates.
   - If the task involves opening/closing balances, period statements, income or expense totals for a bounded period, or comparison across periods, treat reporting-window semantics as material and consult the query-pattern reference before choosing the query shape.
7. Execute the query, inspect the raw result, and sanity-check it before answering.
   - If the result is empty, explain whether that likely means no matching postings, a too-narrow filter, or an account-name mismatch.
   - If the result mixes multiple commodities or lots, explain that `position` and `balance` may be inventories rather than single scalar amounts.
   - If market value conversion or cost basis would materially change the answer, say so explicitly instead of implying a simple cash balance.
   - If BQL cannot answer the question safely, explain the limitation, show the closest safe BQL query or evidence check that was possible, and route mutation requests, advanced valuation decisions, or account-structure decisions to the owning workflow instead of approximating silently.
8. Present the outcome in an audit-friendly way.
   - Show the actual `bean-query` command or the final BQL query.
   - Summarize what the result means in plain language.
   - Call out important caveats such as inventory aggregation, account-pattern assumptions, empty-result ambiguity, or date-window semantics.
   - Offer a narrower follow-up query when the user wants to drill down.
9. Preserve boundaries.
   - Do not mutate `ledger.beancount`, `beancount/**`, or other workspace files in this skill.
   - Follow the shared memory access rules for any reusable learning discovered through query results.
   - Saved Beancount `query` directives are ledger edits; route those requests to the appropriate mutation workflow.
   - If the user wants a transaction entry or minimal transaction-supporting directive, hand off to `$auto-bean-write`.
   - If the request is account structure for an import, hand off to `$auto-bean-import`.
   - For other direct account-structure changes outside import, ask which mutation workflow should own the edit instead of expanding this read-only skill's scope.

Guardrails:

- Keep this skill read-only.
- SHOULD prefer `bean-query` over ad hoc parsing when the question is answerable in BQL.
- Apply the shared fail-closed invariant when account identity, date interpretation, or valuation semantics are ambiguous; because this skill is read-only, return blocker details and required clarification instead of mutating status or ledger files.
- Do not overstate precision when results depend on inventories, costs, or price data the query did not normalize.
- Keep outputs concise, inspectable, and easy to reconcile against the ledger.
