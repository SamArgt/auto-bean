# Workspace Agents

This ledger workspace is prepared for Codex-driven workflows.
This workspace is initialized as a Git repository during `auto-bean init`.

## Purpose

This workspace is the runtime home for a user-owned ledger. Keep product-code changes in the `auto-bean` product repository and keep runtime ledger data, imported statements, and generated artifacts inside this workspace.

Treat Codex and the installed workspace skills as the primary interface for operating here. The coding agent should answer user questions directly, explain what it is doing in workspace terms, and guide the user toward the supported local workflow instead of suggesting a public SDK or external API.

## What The Coding Agent Should Do

- Answer questions about this workspace using the current files and commands in this repo.
- Prefer explaining actions in terms of `ledger.beancount`, `beancount/`, `statements/raw/`, `.auto-bean/`, and `.agents/skills/`.
- Use the installed skills as the primary workflow surface for trust-sensitive structural ledger changes.
- Use the installed `auto-bean-import` skill to normalize raw statement files into inspectable parsed outputs under `statements/parsed/`.
- Use the installed `auto-bean-import` skill to create or extend first-seen account structure directly from parsed statements when imported evidence supports it.
- Treat direct working-tree edits plus post-mutation inspection as the standard structural-change flow.
- Suggest validation with `./scripts/validate-ledger.sh` or `./.venv/bin/bean-check ledger.beancount` before presenting structural ledger edits as ready for commit or push.
- Show a concise summary plus `git diff` before asking whether to commit or push a structural change.
- Suggest inspection with `./scripts/open-fava.sh` or `./.venv/bin/fava ledger.beancount` when the user wants to inspect the current ledger state.
- Keep the user informed about what is supported today versus what is planned for later stories.
- Ask for explicit approval before committing or pushing changes to `ledger.beancount` or files under `beancount/`.


## What The Coding Agent Should Not Do

- Do not treat the product repo as the live ledger workspace.
- Do not invent import commands, APIs, or skills that do not exist in this workspace.
- Do not describe statement intake as a silent ledger mutation workflow; import may mutate bounded account structure, but accepted ledger edits still require validation plus explicit review and approval at the commit/push boundary.
- Do not claim statement intake is ready if `./.venv/bin/docling` is missing or not runnable.
- Do not describe a working-tree mutation as accepted before validation succeeds and the user explicitly approves commit or push finalization.
- Do not treat proposal artifacts as mandatory for every structural edit; they are optional for deeper review and unusually risky changes.

## Workspace Tree

```text
.
|-- AGENTS.md
|-- ledger.beancount
|-- beancount/
|   |-- accounts.beancount
|   `-- opening-balances.beancount
|-- statements/
|   |-- import-status.yml
|   |-- parsed/
|   `-- raw/
|-- scripts/
|   |-- open-fava.sh
|   `-- validate-ledger.sh
|-- .agents/
|   `-- skills/
|       |-- auto-bean-apply/
|       |-- auto-bean-import/
|       `-- shared/
`-- .auto-bean/
    |-- artifacts/
    `-- proposals/
```

## Path Guide

- `ledger.beancount`: stable ledger entrypoint
- `beancount/`: included ledger fragments
- `beancount/accounts.beancount`: preferred home for durable account `open` directives
- `beancount/opening-balances.beancount`: opening balance entries and bootstrap balance context
- `statements/raw/`: raw statement intake boundary; do not rewrite the source files
- `statements/parsed/`: normalized parse outputs produced from raw statements
- `statements/import-status.yml`: durable parse-state index for statement intake
- `.auto-bean/artifacts/`: governed run artifacts and diagnostics
- `.auto-bean/proposals/`: optional proposal documents for riskier or review-heavy changes when deeper inspection is needed
- `.agents/skills/`: installed runtime skills available to the coding agent

## Operating Notes

- Use Git in this workspace to inspect diffs, review history, and create approved commits.
- Review structural ledger changes after mutation, before accepting them into git history.
- Keep governed runtime state under `.auto-bean/` and installed runtime skills under `.agents/skills/`.
- Statement normalization routes through the workspace-local Docling CLI at `./.venv/bin/docling`.
- For account discovery, prefer `beancount/accounts.beancount`; fall back to other included ledger files only when needed.
- Story 2.2 extends import to mutate first-seen account structure directly from parsed evidence, but reconciliation, transaction posting, and durable memory still belong to later or separate reviewed workflows.
- When a structural change is committed, prefer git-backed rollback over a separate proposal-application phase.
