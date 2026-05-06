# Workspace Agents

This is a user-owned ledger workspace. Keep product-code work in the `auto-bean` product repository; keep ledger files, statements, governed runtime state, and installed skills here.

Codex is the orchestrator. Installed skills under `.agents/skills/` are the execution surface.

Context7 MCP is configured for Codex in the gitignored `.codex/config.toml` so skills can look up current external-library documentation. If a Context7 API key was provided during initialization, it is stored in that local config file and must not be committed.

## Quick Start

- Use `$auto-bean-import` for statement imports from `statements/raw/`.
- Use `$auto-bean-query` for read-only ledger analysis through Beancount and `bean-query`.
- Use `$auto-bean-write` for transaction drafting, correction, and transaction-specific validation.
- Use `$auto-bean-memory` for governed persistence of eligible reusable decisions.

High-frequency paths:

- `ledger.beancount`: stable ledger entrypoint
- `beancount/`: included ledger fragments
- `statements/raw/`: raw statement intake
- `statements/parsed/`: normalized statement evidence
- `statements/import-status.yml`: import state

## Import Workflow

Users should start imports with `$auto-bean-import`.

`$auto-bean-import` discovers unprocessed raw statements, skips already-current statements, delegates raw-to-parsed work to `$auto-bean-process`, resolves process artifacts, derives first-seen account structure, delegates categorization/reconciliation/deduplication to `$auto-bean-categorize`, brokers user input, posts transactions with `$auto-bean-write`, and hands governed memory suggestions to `$auto-bean-memory`.

For import workflows, `$auto-bean-import` is the sole broker for final user approval and commit/push readiness.

## User Input

When workflow work needs user input, persist safe deterministic progress first and follow `.agents/skills/shared/question-handling-contract.md`.

After the user answers, resume the same statement, artifact, transaction, or memory operation from existing files with that answer in context.

## Deep Policy

### Review Boundary

Before commit or push for ledger mutations:

- keep parsed statement facts separate from derived ledger edits
- show reconciliation findings and required user decisions
- validate with `./scripts/validate-ledger.sh` or `./.venv/bin/bean-check ledger.beancount`
- summarize changed files and show `git diff`
- make clear that working-tree changes are not accepted into history until the user approves finalization

### Import Status Reference

Read `.agents/skills/shared/import-status-reading.md` for the canonical per-statement status table and recovery rules. A batch import can contain statements in several statuses at once.

Only mark a statement `done` after user approval of the final import result.

### Memory

Read `.agents/skills/shared/memory-access-rules.md` before relying on or requesting durable memory persistence.

Read `.agents/skills/shared/workflow-rules.md`, `.agents/skills/shared/ownership-map.md`, and `.agents/skills/shared/sub-agent-return-examples.md` for shared evidence, artifact privacy, ownership, and sub-agent return expectations.

Skills may suggest useful governed memory. Only `$auto-bean-memory` writes `.auto-bean/memory/**`, and reused memory is advisory, never silent authority.

### Reference Paths

- `.auto-bean/artifacts/`: diagnostics and audit artifacts
- `.auto-bean/artifacts/categorize/`: optional categorization, reconciliation, deduplication, and user-input artifacts
- `.auto-bean/artifacts/import/`: statement-scoped import provenance and import-brokered answers
- `.auto-bean/artifacts/process/`: raw-to-parsed processing notes, warnings, and process questions
- `.auto-bean/memory/`: governed memory
- `.agents/skills/`: installed runtime skills
- `.codex/config.toml`: gitignored project-scoped Codex MCP configuration for Context7

### Guardrails

Always:

- route ledger reads through `$auto-bean-query` when Beancount can answer them
- route transaction writing through `$auto-bean-write`
- validate ledger mutations before final review
- keep working-tree changes separate from accepted history until the user approves finalization

Never:

- treat the product repo as the live ledger workspace
- treat unapproved working-tree changes as finalized
- bypass `$auto-bean-import` for import final approval, commit readiness, or push readiness

Prefer git-backed revert for committed recovery.
