---
name: auto-bean-query
description: Read-only Beancount analysis with bean-query. Use for balances, account activity, period reports, account discovery, or transaction inspection.
---

Read [common guidance](../../references/common.md) once per execution context. Query may prepare its disposable base runtime but never edits financial files, evidence, status, memory or workspace instructions.

1. Resolve the root ledger (`ledger.beancount` by default), include graph, existing accounts and configured account roots. Translate the question into bounded accounts, dates and outputs.
2. Use `auto_bean bean-query ledger.beancount 'SELECT ...'`, starting with summaries and then targeted registers. Use BQL for queryable facts. Read [query patterns](../../references/ledger-reference.md#querying) only when choosing an unfamiliar query, reporting window or inventory reduction; read [directives](../../references/ledger-reference.md#directives) when account or balance-assertion semantics matter.
3. Inspect results before explaining them. Distinguish no matches from a wrong filter, and holdings from cost basis or market value. Qualify partial results when loader errors prevent a reliable answer. Use authoritative documentation for unresolved semantics.
4. Return the actual query, concise interpretation, reporting dates and material caveats. Route transaction changes to `$auto-bean:auto-bean-write`, prices to `$auto-bean:auto-bean-prices`, and import account structure to `$auto-bean:auto-bean-import`; this skill remains read-only, including saved `query` directives.

For an import, query actual ledger files and identify the query date and provenance. Disclose incomplete or unvalidated import entries; they are not accepted history. Use source/record identifiers to distinguish already-written entries during recovery. Planned postings remain in parsed JSON and must not be described as existing ledger balances.
