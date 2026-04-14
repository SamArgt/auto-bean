# Workspace Agents

This workspace is the runtime home for a user-owned ledger.
Keep product-code work in the `auto-bean` product repository.
Keep ledger files, statements, governed runtime state, and installed skills in this workspace.

Treat Codex as the orchestrator.
Treat the installed skills under `.agents/skills/` as the execution surface for trust-sensitive work.


Read these references before acting:


## Import Workflow

Use one explicit two-step workflow for import-driven ledger changes:

1. `auto-bean-import`
   - normalize raw statements into reviewed evidence under `statements/parsed/`
   - update `statements/import-status.yml` to `parsed` or `parsed_with_warnings`
   - create first-seen account structure only when the evidence is strong enough
   - prepare the evidence handoff for posting work
2. `auto-bean-apply`
   - take already-reviewed evidence from `statements/parsed/`
   - derive candidate ledger postings
   - update `statements/import-status.yml` to `in_review` after writing import-derived Beancount transactions
   - validate, summarize, and show `git diff`
   - ask for explicit approval before commit or push, then move finalized statements to `done`

Do not blur those responsibilities.
`auto-bean-import` prepares evidence.
`auto-bean-apply` performs reviewed posting mutation.

Use only these workflow statuses in `statements/import-status.yml`:

- `ready`: no actions have been taken yet; ready for import
- `parsed`: parsed but no transactions have been posted to the workspace
- `parsed_with_warnings`: parsed but there are warnings to work on before transactions are ready to post
- `in_review`: transactions have been posted but not yet validated
- `done`: the workflow is complete

## Worker Handoff

When the import job is large, the main agent may use a worker to run the staged process:

1. one worker handles the `auto-bean-import` stage
2. one worker handles the `auto-bean-apply` stage

Keep the handoff explicit between those two stages.
Keep final review, validation interpretation, memory writes, and commit/push approval with the main agent.
Once the whole two-step workflow reaches its finalized outcome, update the relevant `statements/import-status.yml` entries to `done`.

## Memory Ownership

Skills may suggest useful repeated-import memory.
The orchestrator decides whether that memory should actually be written.

### Source context memory

Read this reference file before writing any source-context memory: `.agents/skills/auto-bean-import/references/import-source-context.example.json`

Write repeated-import source context only under `.auto-bean/memory/import_sources/` and only after a trustworthy finalized outcome.
Do not write memory for blocked, rejected, validation-failed, ambiguous, or deferred runs.
Treat reused memory as advisory guidance, never silent authority.

## Review Boundary

Before any commit or push for ledger mutations:

- keep parsed statement facts separate from derived ledger edits
- Validate the ledger integrity with `./scripts/validate-ledger.sh` or `./.venv/bin/bean-check ledger.beancount` and show the validation outcome
- summarize what changed, why, and which files are affected
- make it clear the working tree may have changed without being accepted into git history

The user may stop, defer, or reject finalization.

## Workspace Paths

- `ledger.beancount`: stable ledger entrypoint
- `beancount/`: included ledger fragments
- `statements/raw/`: raw statement intake boundary
- `statements/parsed/`: reviewed normalized statement evidence
- `statements/import-status.yml`: parse-state index
- `.auto-bean/artifacts/`: diagnostics and audit artifacts
- `.auto-bean/memory/import_sources/`: orchestrator-owned repeated-import source context
- `.agents/skills/`: installed runtime skills

## Guardrails

- Do not treat the product repo as the live ledger workspace.
- Do not invent workflows, commands, or skills that are not present here.
- Do not describe a working-tree mutation as accepted before validation succeeds and the user approves finalization.
- Do not make proposal artifacts mandatory for routine changes.
