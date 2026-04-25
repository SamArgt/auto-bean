# Import-Owned Artifact Contract

`$auto-bean-import` owns one global audit artifact for each active import under `.auto-bean/artifacts/import/`. Worker skills may report paths, questions, findings, and suggestions, but they do not create or update this global artifact.

The import artifact is an orchestration audit surface, not a replacement for stage-owned artifacts. It records links, stable ids, short summaries, handoff state, user decisions brokered by `$auto-bean-import`, and final readiness. It must not duplicate or re-author the detailed raw-to-parsed evidence owned by `$auto-bean-process` or the detailed categorization, reconciliation, and deduplication analysis owned by `$auto-bean-categorize`.

## Path

Use a deterministic Markdown file path for the active import, such as `.auto-bean/artifacts/import/current-import.md`. If multiple independent imports are active, use one stable Markdown file per import batch, named from the batch id or source fingerprint set. Keep all paths inside `.auto-bean/artifacts/import/`.

## Format

Optimize the artifact for human review. Use Markdown headings, compact tables, checklists, and short bullets. Use stable ids for statements, questions, decisions, and handoffs so later updates can replace the relevant section deterministically.

Prefer readable Markdown over large structured-data blocks. Use fenced code blocks only for short exact values that need to be copied or audited, such as proposed Beancount directives, validation command output summaries, or small transaction excerpts.

## Required Sections

Record these sections before the workflow can be considered ready for final review:

- `# Import <import_id>` with `schema_version: 1`, the stable import id, `created_at`, and `updated_at`
- `## Workflow State`: summary counts and the highest status reached
- `## Stage Ownership`: the authoritative owner for process, import, categorize, write, and memory stages
- `## Statements`: one entry per source path with fingerprint, parsed artifact path, current status, stage artifact paths, blocker summaries, and validation state
- `## Questions`: unresolved and answered process, first-seen-account, categorize, and write-stage questions with stable ids, answers, owning stage, source artifact paths, and resume status
- `## First-Seen Account Decisions`: proposed, approved, rejected, or written account-opening decisions with target files, evidence, validation result, and user approval context
- `## Posting Handoffs`: transaction-writing inputs handed to `$auto-bean-write`, write result, validation result, and final-review readiness
- `## Memory Candidates`: reusable-learning candidates summarized from worker returns or user-approved import decisions, with provenance, originating artifact path, source statement, user approval state, eligibility, and deduplication status
- `## Ignored Or Rejected Inputs`: path-unsafe artifacts, stale files, invalid suggestions, unresolved blockers, or memory candidates rejected from governed handoff

## Ownership Boundaries

- For `$auto-bean-process`, record only parse status, parsed output path, process question artifact path, warning or blocker summaries, retry/manual-resolution metadata, and import-brokered answers. Do not copy full parsed payloads, redo normalization, or reinterpret raw statement evidence in this artifact.
- For `$auto-bean-categorize`, record only categorize artifact paths, finding summaries, posting-readiness state, unresolved or answered question ids, memory-suggestion provenance, and import-brokered answers. Do not copy the full categorization analysis, rewrite reconciliation or deduplication findings, or make category decisions that belong to `$auto-bean-categorize`.
- If the human-readable import summary needs detail from a worker-owned artifact, link to that artifact and summarize only the import decision or blocker that affects orchestration.
- Import-owned first-seen account decisions, write handoffs, final-review readiness, status transitions, and governed memory handoff state may be recorded in detail because those belong to `$auto-bean-import`.

## Update Rules

- Update the artifact whenever `$auto-bean-import` changes a statement status, records or resolves a user question, writes first-seen account directives, invokes `$auto-bean-write`, receives validation output, changes final-review readiness, or prepares the governed memory handoff.
- Treat `statements/import-status.yml` as the compact orchestration index and this import artifact as the richer audit surface. Keep their statuses consistent.
- Persist every import-owned decision here before asking the user for approval, handing work to another stage, invoking `$auto-bean-memory`, or marking a statement `done`.
- Store summaries, paths, stable ids, and evidence references. Do not copy raw statement dumps, full parsed statement payloads, complete ledgers, or unrelated financial data into this artifact.
- Fail closed when the artifact path would escape `.auto-bean/artifacts/import/`, when the active import artifact cannot be read or updated, or when its status conflicts with `statements/import-status.yml`.

## Memory Handoff

Before invoking `$auto-bean-memory`, `$auto-bean-import` must pass the current import artifact path as source/audit context along with eligible memory suggestions and completed stage artifacts. `$auto-bean-memory` may use the import artifact to validate provenance and approval state, but durable memory records still store only reusable operational learning through the governed memory workflow.
