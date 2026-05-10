# Import-Owned Artifact Contract

`$auto-bean-import` owns one Markdown decision artifact per raw statement under `.auto-bean/artifacts/import/`. Sub-agent stages may report paths, question ids, findings, and suggestions, but they do not create or update import-owned artifacts.

The import artifact stores statement-scoped decisions and provenance: stable ids, import-brokered user decisions, memory suggestions, and references to source, parsed, process, categorize, write, validation, and memory artifacts.

Stage-owned detail remains in the owning artifact. Process artifacts own processing warnings, questions, and answers. Categorize artifacts own categorization, reconciliation, and deduplication warnings, questions, and answers. Import artifacts own first-seen account, write-stage, final approval, and import-brokered decisions. `statements/import-status.yml` owns operational state.

## Path

Use a deterministic Markdown file path for each raw statement. The filename prefix must match the corresponding raw statement's artifact prefix and must be shared by artifacts from `$auto-bean-process`, `$auto-bean-categorize`, and `$auto-bean-import`.

Example for `statements/raw/checking/jan-2026.pdf`:

- process artifact: `.auto-bean/artifacts/process/checking-jan-2026--process.md`
- categorize artifact: `.auto-bean/artifacts/categorize/checking-jan-2026--categorize.md`
- import artifact: `.auto-bean/artifacts/import/checking-jan-2026--import.md`

SHOULD prefer the raw filename stem as the prefix after normalizing it to a filesystem-safe slug. If two raw statements would produce the same prefix, add the minimal parent-directory slug or fingerprint suffix needed to make the prefix unique, then use that same disambiguated prefix for every artifact related to that raw statement. Keep all import-owned paths inside `.auto-bean/artifacts/import/`. Do not create one global file or one batch artifact for multiple raw statements.

## Format

Optimize the artifact for human review. Use Markdown headings, compact tables, checklists, and short bullets. Use stable ids for statements, questions, decisions, and handoffs so later updates can replace the relevant section deterministically.

SHOULD prefer readable Markdown over large structured-data blocks. Use fenced code blocks only for short exact values that need to be copied or audited, such as proposed Beancount directives, validation command output summaries, or small transaction excerpts.

## Required Sections

Record these sections before the workflow can be considered ready for final review:

- `# Import Decisions <artifact_prefix>` with `schema_version: 1`, the stable raw statement path, source fingerprint, `artifact_prefix`, `created_at`, and `updated_at`
- `## Stage Ownership`: the authoritative owner for process, import, categorize, write, and memory stages
- `## Artifact References`: source path, parsed artifact path, process artifact path, categorize artifact path, write/validation references, and any memory handoff references
- `## Questions`: import-owned unresolved and answered first-seen-account, write-stage, final-approval, and import-brokered questions with stable ids, answers, owning stage, source artifact paths, and resolution notes; for process and categorize questions, store only ids, source artifact paths, and import-level resume decisions while the full question and answer payloads remain in the owning process or categorize artifact
- `## First-Seen Account Decisions`: proposed, approved, rejected, or written account-opening decisions with target files, evidence references, validation references, and user approval context
- `## Memory Attribution`: governed memory records considered or used by `$auto-bean-import`, including `import_source_behavior` hints used for processing handoff or first-seen account inspection, current-evidence checks, and rejection reasons for skipped memory
- `## Cross-Statement Review`: import-batch transfer or duplicate candidates spanning multiple categorize artifacts, with paired artifact paths, stable transaction references, matched facts, user question ids, decision state, and posting-decision impact
- `## Posting Decisions`: transaction-writing inputs or decisions handed to `$auto-bean-write`, write result references, validation references, and user approval context
- `## Memory Candidates`: reusable-learning candidates summarized from sub-agent returns or import decisions, with provenance, originating artifact path, source statement, review or eligibility state, and deduplication status
- `## Ignored Or Rejected Inputs`: path-unsafe artifacts, stale files, invalid suggestions, unresolved blockers, or memory candidates rejected from governed handoff

Do not include workflow counts, current status, highest status reached, retry counters, status transition logs, queue position, batch progress, or other operational import state. That information belongs in `statements/import-status.yml`.

## Ownership Boundaries

- For `$auto-bean-process`, record only parsed output paths, process artifact paths, warning or blocker presence flags that require an import-owned decision, processing-related memory suggestion summaries, and import-brokered answer ids or resume decisions. Do not copy process warning text, question text, answer text, parse status, retry/manual-resolution metadata, full parsed payloads, redo normalization, or reinterpret raw statement evidence in this artifact.
- For `$auto-bean-categorize`, record only categorize artifact paths, finding summaries that require an import-owned decision, cross-statement review summaries, unresolved or answered question ids, memory-suggestion provenance, and import-brokered answer ids or resume decisions. Do not copy categorize warning text, question text, answer text, categorization status, posting-readiness state, the full categorization analysis, rewrite statement-local reconciliation or deduplication findings, or make category decisions that belong to `$auto-bean-categorize`.
- `$auto-bean-import` may append or update clearly labeled `Import Batch Cross-Statement Review` notes in categorize artifacts when a transfer or duplicate candidate spans multiple statements. Keep those notes limited to paired artifact paths, stable transaction references, matched facts, confidence, suggested action, and question ids; resume `$auto-bean-categorize` instead when statement-local categorization must be recomputed.
- If the human-readable import summary needs detail from a stage-owned artifact, link to that artifact and summarize only the import decision or blocker that affects orchestration.
- Import-owned first-seen account decisions, write handoffs, user approval decisions, and governed memory handoff decisions may be recorded in detail because those belong to `$auto-bean-import`.
- For `import_source_behavior` memory, record only the memory path, stable summary, matched current evidence, decision influenced, and limits on reuse. Do not copy entire memory files into the import artifact.

Allowed compact detail examples:

- `question_id: cat-q-014`, `source_artifact: .auto-bean/artifacts/categorize/checking-jan-2026--categorize.md`, `decision: pending`.
- `finding: possible duplicate`, `paired_artifact: .auto-bean/artifacts/categorize/card-jan-2026--categorize.md`, `matched_facts: date, amount, external_id`, `action: broker user decision`.
- `memory_candidate: category_mapping`, `origin: cat-q-014`, `source_artifact: ...--categorize.md`, `eligibility: ready_for_memory_handoff`.

Forbidden copied detail examples:

- Full process or categorize question bodies copied into `## Questions`.
- Full warning narratives, parser stdout/stderr, parsed JSON records, or statement-local categorization analysis copied from stage-owned artifacts.
- Complete memory records or full import-source behavior files copied into `## Memory Attribution`.

## Update Rules

- Update the artifact whenever `$auto-bean-import` records or resolves an import-owned user question, makes a first-seen account decision, records a cross-statement transfer or duplicate review candidate, invokes `$auto-bean-write`, receives validation output that informs a decision, asks for final user approval, or prepares the governed memory handoff. If the question belongs to a stage-owned artifact, update that individual artifact with the full answer and keep only ids, paths, and import-level decisions here.
- Treat `statements/import-status.yml` as the only orchestration status index. The import artifact may reference the matching status entry path or key, but it must not duplicate current status or progress fields.
- When artifact references conflict with `statements/import-status.yml`, use the shared status/artifact reconciliation hierarchy: source-file reality, status operational pointers, artifact references, then fail closed with a brokered repair question when unresolved.
- Persist every import-owned decision here before asking the user for approval, handing work to another stage, invoking `$auto-bean-memory`, or marking the matching status entry `done`.
- Store summaries, paths, stable ids, and evidence references. Do not copy raw statement dumps, full parsed statement payloads, complete ledgers, or unrelated financial data into this artifact.
- Apply the shared fail-closed invariant when the artifact path would escape `.auto-bean/artifacts/import/`, when the source prefix does not match the raw statement's process and categorize artifacts, when the import artifact cannot be read or updated, or when artifact references conflict with `statements/import-status.yml`.

## Memory Handoff

Before invoking `$auto-bean-memory`, `$auto-bean-import` must pass the relevant statement-scoped import artifact paths as source/audit context along with eligible memory suggestions and completed stage artifacts. `$auto-bean-memory` may use import artifacts to validate provenance, review state, and eligibility, but durable memory records still store only reusable operational learning through the governed memory workflow.
