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
- Suggest validation with `./scripts/validate-ledger.sh` or `./.venv/bin/bean-check ledger.beancount` before presenting ledger edits as ready.
- Suggest inspection with `./scripts/open-fava.sh` or `./.venv/bin/fava ledger.beancount` when the user wants to inspect the current ledger state.
- Keep the user informed about what is supported today versus what is planned for later stories.
- Ask for explicit approval before committing changes to `ledger.beancount` or files under `beancount/`.

## What The Coding Agent Should Not Do

- Do not treat the product repo as the live ledger workspace.
- Do not invent import commands, APIs, or skills that do not exist in this workspace.
- Do not describe statement intake as a ledger mutation workflow; this story only normalizes files into `statements/parsed/` and updates `statements/import-status.yml`.
- Do not claim statement intake is ready if `./.venv/bin/docling` is missing or not runnable.
- Do not commit structural ledger changes before the user has explicitly approved the validated proposal.

## Workspace Tree

```text
.
|-- AGENTS.md
|-- ledger.beancount
|-- beancount/
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
- `statements/raw/`: raw statement intake boundary; do not rewrite the source files
- `statements/parsed/`: normalized parse outputs produced from raw statements
- `statements/import-status.yml`: durable parse-state index for statement intake
- `.auto-bean/artifacts/`: governed run artifacts and diagnostics
- `.auto-bean/proposals/`: proposal documents for riskier or review-heavy changes
- `.agents/skills/`: installed runtime skills available to the coding agent

## Operating Notes

- Use Git in this workspace to inspect diffs, review history, and create approved commits.
- Review structural ledger changes before accepting them into the ledger.
- Keep governed runtime state under `.auto-bean/` and installed runtime skills under `.agents/skills/`.
- Statement normalization routes through the workspace-local Docling CLI at `./.venv/bin/docling`.
- Story 2.1 stops at normalized parse files and parse diagnostics; later stories handle review, account proposals, reconciliation, mutation, and memory.
