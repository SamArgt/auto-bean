---
name: auto-bean-query
description: Read-only Beancount analysis with bean-query. Use for balances, account activity, period reports, account discovery, or transaction inspection.
---

Read [plugin execution](../../references/plugin-execution.md) and relevant workspace `.auto-bean/memory/MEMORY.md` context. Query may prepare its disposable base runtime but never edits financial files, evidence, status, memory, or workspace instructions.

1. Resolve the root ledger (`ledger.beancount` by default), include graph, existing account names, and configured account roots. Translate the question into bounded accounts, dates, and outputs.
2. Use `auto_bean bean-query ledger.beancount 'SELECT ...'`. Prefer summaries, then targeted registers. Use BQL instead of grepping transaction text for queryable facts.
3. Read [query patterns](references/bean-query-patterns.md) when choosing an unfamiliar query, reporting window, or inventory reduction. Opening/closing boundaries are material: dates start inclusive and end exclusive. To include March 31, use `CLOSE ON 2026-04-01`; a Beancount `balance` assertion applies before transactions on its date.
4. Use authoritative Beanquery/Beancount documentation through Context7 or official sites for unresolved syntax or semantics. Read [ledger semantics](../../references/beancount-syntax-and-best-practices.md) only when directive, currency, or account constraints matter. Read [memory rules](../../references/memory-access-rules.md) only when verifying advisory hints or returning reusable learning.
5. Inspect results before explaining them. Distinguish no matches from a wrong filter; distinguish units, lot cost, and market value. Mixed-commodity inventories are not one scalar balance. Do not silently treat unapproved working-tree candidates as accepted history; disclose their effect and exclude them for import duplicate/balance decisions where required.
6. Show the actual query, a concise interpretation, and material caveats. On ambiguity or loader errors, explain the limitation and required repair; qualify any partial result. Do not change status to answer a read-only question.

Route transaction mutations to `$auto-bean:auto-bean-write`, prices to `$auto-bean:auto-bean-prices`, and import account structure to `$auto-bean:auto-bean-import`. Other structural changes need an explicitly scoped mutation request; this skill remains read-only, including saved `query` directives.
