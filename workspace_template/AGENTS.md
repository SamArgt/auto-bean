# Workspace Agents

This workspace is the runtime home for a user-owned ledger.
Keep product-code work in the `auto-bean` product repository.
Keep ledger files, statements, governed runtime state, and installed skills in this workspace.

Treat Codex as the orchestrator.
Treat the installed skills under `.agents/skills/` as the execution surface for trust-sensitive work.


Read these references before acting:


## Foundation Skills

Use the installed foundation skills for ledger-specific work:

- `auto-bean-query`: read-only ledger analysis through Beancount and `bean-query`
- `auto-bean-write`: transaction drafting, correction, validation, and transaction-specific clarification

Workflow skills may orchestrate these foundation skills, but should not duplicate their procedures.
Use `auto-bean-query` whenever a decision depends on balances, account activity, date-bounded totals, register rows, transaction existence, duplicate exploration, or other ledger reads.
Use `auto-bean-write` whenever a workflow needs to add or correct Beancount transaction entries.

## Import Workflow

Use one explicit two-step workflow for import-driven ledger changes:

1. `auto-bean-import` skill
   - normalize raw statements into reviewed evidence under `statements/parsed/`
   - update `statements/import-status.yml` to `parsed` or `parsed_with_warnings`
   - use `auto-bean-query` when import decisions require ledger analysis rather than structure inspection
   - create first-seen account structure only when the evidence is strong enough
   - prepare the evidence handoff for posting work
2. `auto-bean-apply` skill
   - take already-reviewed evidence from `statements/parsed/`
   - use `auto-bean-query` for ledger reads needed during posting review and reconciliation
   - use `auto-bean-write` to draft or correct candidate Beancount transaction postings directly in the workspace
   - run reconciliation checks for likely transfers, possible duplicates, unbalanced outcomes, currency risk, and possible future transfers
   - stop and ask the user a bounded clarification question when a risky interpretation remains ambiguous or unfamiliar
   - update `statements/import-status.yml` to `in_review` after writing import-derived Beancount transactions
   - validate, summarize, show findings plus suggested actions, show how clarification answers changed the pending result when needed, and show `git diff`
   - if a clarification reveals a reusable source-specific rule, suggest a bounded source-context memory update for review
   - ask the user for a decision on each finding, apply those decisions, then ask for explicit final approval before commit or push

Do not blur those responsibilities.
`auto-bean-import` prepares evidence.
`auto-bean-apply` coordinates reviewed posting mutation, reconciliation decisions, status transitions, and finalization.

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
- keep reconciliation findings explicit, with one user decision required for each finding before action is taken
- Validate the ledger integrity with `./scripts/validate-ledger.sh` or `./.venv/bin/bean-check ledger.beancount` and show the validation outcome
- distinguish confirmed validation failures from inferred risks or user concerns
- summarize what changed, why, and which files are affected
- make it clear the working tree may have changed without being accepted into git history

The user may stop, defer, or reject finalization.
If a committed mutation later needs to be undone, prefer reverting the recorded commit instead of silently replacing ledger files.

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
- Do not bypass `auto-bean-query` for ledger analysis or `auto-bean-write` for transaction writing when those narrower skills fit the task.
- Do not describe a working-tree mutation as accepted before validation succeeds and the user approves finalization.
- Do not make proposal artifacts mandatory for routine changes.
- Do not describe committed rollback as ad hoc file replacement when git-backed revert is available.
