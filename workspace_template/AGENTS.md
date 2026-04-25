# Workspace Agents

This is a user-owned ledger workspace. Keep product-code work in the `auto-bean` product repository; keep ledger files, statements, governed runtime state, and installed skills here.

Codex is the orchestrator. Installed skills under `.agents/skills/` are the execution surface.

## Core Skills

- `auto-bean-query`: read-only ledger analysis through Beancount and `bean-query`
- `auto-bean-write`: transaction drafting, correction, and transaction-specific validation
- `auto-bean-memory`: governed persistence of approved reusable decisions

Use `auto-bean-query` for balances, account activity, date windows, register rows, transaction existence, duplicates, and other ledger reads.
Use `auto-bean-write` when a workflow needs to add or correct Beancount transaction entries.

## Import Workflow

Users should start imports with `$auto-bean-import`.

`auto-bean-import` discovers unprocessed raw statements, skips already-current statements, uses sub-agents for bounded statement work, delegates raw-to-parsed work to `$auto-bean-process`, resolves any process question artifacts and updates intermediate statements, derives first-seen account structure, delegates categorization/reconciliation/deduplication work to `$auto-bean-categorize`, asks the user for needed input, posts transactions with `$auto-bean-write`, and handles governed memory suggestions through `$auto-bean-memory` at the end.

Workflow statuses in `statements/import-status.yml`:

- `ready`: no successful parsed evidence exists yet
- `parsed`: parsed evidence exists and is ready for posting work
- `parsed_with_warnings`: parsed evidence exists but warnings need review
- `in_review`: import-derived transactions have been written but not finalized
- `done`: the full import workflow is complete

Only mark a statement `done` after user approval of the final import result.

## User Input

When any skill needs user input, first keep working through every safe deterministic step. Write or update the relevant parsed artifacts, status entries, ledger draft comments, warnings, or blocking issues so the workspace clearly shows what is complete and what still requires the user.

Ask bounded questions with the appropriate user-input tool or conversation channel only after that progress is persisted. Include where the pending question is recorded, why guessing is unsafe, and the smallest useful set of choices or requested facts.

After the user answers, resume the same statement, artifact, transaction, or memory operation from the existing files with that answer in context. Do not restart from the beginning or treat clarification as a terminal blocked state unless the answer remains insufficient after a bounded follow-up.

## Memory

Read `.agents/skills/shared/memory-access-rules.md` before relying on or requesting durable memory persistence.

Skills may suggest useful governed memory. Only `auto-bean-memory` writes `.auto-bean/memory/**`, and only for approved reusable outcomes. Treat reused memory as advisory guidance, never silent authority.

## Review Boundary

Before commit or push for ledger mutations:

- keep parsed statement facts separate from derived ledger edits
- show reconciliation findings and required user decisions
- validate with `./scripts/validate-ledger.sh` or `./.venv/bin/bean-check ledger.beancount`
- summarize changed files and show `git diff`
- make clear that working-tree changes are not accepted into history until the user approves finalization

## Paths

- `ledger.beancount`: stable ledger entrypoint
- `beancount/`: included ledger fragments
- `statements/raw/`: raw statement intake
- `statements/parsed/`: normalized statement evidence
- `statements/import-status.yml`: import state
- `.auto-bean/artifacts/`: diagnostics and audit artifacts
- `.auto-bean/artifacts/categorize/`: optional categorization, reconciliation, deduplication, and user-input artifacts
- `.auto-bean/memory/`: governed memory
- `.agents/skills/`: installed runtime skills

## Guardrails

- Do not treat the product repo as the live ledger workspace.
- Do not bypass `auto-bean-query` for ledger analysis or `auto-bean-write` for transaction writing.
- Do not call ledger mutations accepted before validation succeeds and the user approves finalization.
- Prefer git-backed revert for committed recovery.
