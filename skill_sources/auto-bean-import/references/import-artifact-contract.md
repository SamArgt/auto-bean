# Import-Owned Artifact Contract

`$auto-bean-import` owns one Markdown decision artifact per raw statement under `.auto-bean/artifacts/import/`. Worker skills may report paths, questions, findings, and suggestions, but they do not create or update import-owned artifacts.

The import artifact is a statement-scoped decision and provenance surface, not a status tracker and not a replacement for stage-owned artifacts. It records stable ids, key user or agent decisions brokered by `$auto-bean-import`, pending or answered questions, memory suggestions, and references to source, parsed, process, categorize, write, validation, and memory artifacts. It must not duplicate operational state from `statements/import-status.yml`, re-author the detailed raw-to-parsed evidence owned by `$auto-bean-process`, or re-author the detailed categorization, reconciliation, and deduplication analysis owned by `$auto-bean-categorize`.

## Path

Use a deterministic Markdown file path for each raw statement. The filename prefix must match the corresponding raw statement's artifact prefix and must be shared by artifacts from `$auto-bean-process`, `$auto-bean-categorize`, and `$auto-bean-import`.

Example for `statements/raw/checking/jan-2026.pdf`:

- process artifact: `.auto-bean/artifacts/process/checking-jan-2026--process.md`
- categorize artifact: `.auto-bean/artifacts/categorize/checking-jan-2026--categorize.md`
- import artifact: `.auto-bean/artifacts/import/checking-jan-2026--import.md`

Prefer the raw filename stem as the prefix after normalizing it to a filesystem-safe slug. If two raw statements would produce the same prefix, add the minimal parent-directory slug or fingerprint suffix needed to make the prefix unique, then use that same disambiguated prefix for every artifact related to that raw statement. Keep all import-owned paths inside `.auto-bean/artifacts/import/`. Do not create one global file or one batch artifact for multiple raw statements.

## Format

Optimize the artifact for human review. Use Markdown headings, compact tables, checklists, and short bullets. Use stable ids for statements, questions, decisions, and handoffs so later updates can replace the relevant section deterministically.

Prefer readable Markdown over large structured-data blocks. Use fenced code blocks only for short exact values that need to be copied or audited, such as proposed Beancount directives, validation command output summaries, or small transaction excerpts.

## Required Sections

Record these sections before the workflow can be considered ready for final review:

- `# Import Decisions <artifact_prefix>` with `schema_version: 1`, the stable raw statement path, source fingerprint, `artifact_prefix`, `created_at`, and `updated_at`
- `## Stage Ownership`: the authoritative owner for process, import, categorize, write, and memory stages
- `## Artifact References`: source path, parsed artifact path, process artifact path, categorize artifact path, write/validation references, and any memory handoff references
- `## Questions`: unresolved and answered process, first-seen-account, categorize, and write-stage questions with stable ids, answers, owning stage, source artifact paths, and resolution notes
- `## First-Seen Account Decisions`: proposed, approved, rejected, or written account-opening decisions with target files, evidence references, validation references, and user approval context
- `## Memory Attribution`: governed memory records considered or used by `$auto-bean-import`, including `import_source_behavior` hints used for processing handoff or first-seen account inspection, current-evidence checks, and rejection reasons for skipped memory
- `## Posting Decisions`: transaction-writing inputs or decisions handed to `$auto-bean-write`, write result references, validation references, and user approval context
- `## Memory Candidates`: reusable-learning candidates summarized from worker returns or user-approved import decisions, with provenance, originating artifact path, source statement, user approval state, eligibility, and deduplication status
- `## Ignored Or Rejected Inputs`: path-unsafe artifacts, stale files, invalid suggestions, unresolved blockers, or memory candidates rejected from governed handoff

Do not include workflow counts, current status, highest status reached, retry counters, status transition logs, queue position, batch progress, or other operational import state. That information belongs in `statements/import-status.yml`.

## Ownership Boundaries

- For `$auto-bean-process`, record only parsed output paths, process artifact paths, warning or blocker summaries that require an import-owned decision, processing-related memory suggestion summaries, and import-brokered answers. Do not copy parse status, retry/manual-resolution metadata, full parsed payloads, redo normalization, or reinterpret raw statement evidence in this artifact.
- For `$auto-bean-categorize`, record only categorize artifact paths, finding summaries that require an import-owned decision, unresolved or answered question ids, memory-suggestion provenance, and import-brokered answers. Do not copy categorization status, posting-readiness state, the full categorization analysis, rewrite reconciliation or deduplication findings, or make category decisions that belong to `$auto-bean-categorize`.
- If the human-readable import summary needs detail from a worker-owned artifact, link to that artifact and summarize only the import decision or blocker that affects orchestration.
- Import-owned first-seen account decisions, write handoffs, user approval decisions, and governed memory handoff decisions may be recorded in detail because those belong to `$auto-bean-import`.
- For `import_source_behavior` memory, record only the memory path, stable summary, matched current evidence, decision influenced, and limits on reuse. Do not copy entire memory files into the import artifact.

## Update Rules

- Update the artifact whenever `$auto-bean-import` records or resolves a user question, makes a first-seen account decision, invokes `$auto-bean-write`, receives validation output that informs a decision, asks for final user approval, or prepares the governed memory handoff.
- Treat `statements/import-status.yml` as the only orchestration status index. The import artifact may reference the matching status entry path or key, but it must not duplicate current status or progress fields.
- Persist every import-owned decision here before asking the user for approval, handing work to another stage, invoking `$auto-bean-memory`, or marking the matching status entry `done`.
- Store summaries, paths, stable ids, and evidence references. Do not copy raw statement dumps, full parsed statement payloads, complete ledgers, or unrelated financial data into this artifact.
- Fail closed when the artifact path would escape `.auto-bean/artifacts/import/`, when the source prefix does not match the raw statement's process and categorize artifacts, when the import artifact cannot be read or updated, or when artifact references conflict with `statements/import-status.yml`.

## Memory Handoff

Before invoking `$auto-bean-memory`, `$auto-bean-import` must pass the relevant statement-scoped import artifact paths as source/audit context along with eligible memory suggestions and completed stage artifacts. `$auto-bean-memory` may use import artifacts to validate provenance and approval state, but durable memory records still store only reusable operational learning through the governed memory workflow.
