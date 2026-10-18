# Ledger Workspace

This directory contains a user-owned Beancount ledger. Use the installed Auto Bean plugin to operate it. Keep product implementation work in the product repository.

- Read `.auto-bean/memory/MEMORY.md` at session start and include relevant context in sub-agent handoffs.
- Use `$auto-bean:auto-bean-import` for statement imports, `$auto-bean:auto-bean-query` for ledger reads, `$auto-bean:auto-bean-write` for transactions, `$auto-bean:auto-bean-prices` for commodity prices, and `$auto-bean:auto-bean-memory` for eligible governed learning.
- Each selected plugin skill supplies current workflow rules, reference locations, and runtime commands. Resolve them from that installed skill. Do not install product copies here.
- If this is a legacy workspace without `.auto-bean/workspace.json`, use `$auto-bean:auto-bean-migrate` before operating it.
- Keep the stable ledger entrypoint in `ledger.beancount`, included fragments in `beancount/`, raw statements in `statements/raw/`, normalized evidence in `statements/parsed/`, and workflow status in `statements/import-status.yml`.
- Keep governed state and artifacts under `.auto-bean/`. Reuse memory as advice supported by current evidence. Route eligible learning through the memory skill; do not write user financial decisions into plugin files.
- Validate ledger edits, explain reconciliation findings, and show the changed files and relevant diff before final review. Working-tree edits become accepted history only after explicit user approval. The import skill owns import approval and statement finalization.
- Preserve unresolved work and user changes. Do not commit or push without authorization.
