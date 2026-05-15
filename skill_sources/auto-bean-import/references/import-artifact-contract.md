# Import Artifact Contract

`$auto-bean-import` owns one statement-scoped Markdown artifact per raw statement. Use it to preserve import decisions, provenance, review state, and handoff references that must survive resumes.

## Creation

- Store artifacts under `.auto-bean/artifacts/import/`.
- Name each file `<artifact_prefix>--import.md`.
- Derive `artifact_prefix` from the raw filename stem as a safe slug; add the smallest parent-directory slug or fingerprint suffix needed for uniqueness.
- Use the same `artifact_prefix` for that raw statement's process, categorize, and import artifacts.
- Create or refresh the artifact before the statement leaves `raw_ready`.
- Never create one global import artifact or one batch artifact for multiple statements.

## Format

- Keep the artifact human-readable Markdown.
- Use stable ids for statements, questions, decisions, document references, posting handoffs, and memory candidates.
- Prefer compact tables, checklists, and short bullets.
- Use fenced blocks only for short exact values that need audit, such as proposed Beancount directives or validation summaries.

## Required Content

Include these sections when relevant:

- `# Import Decisions <artifact_prefix>` with `schema_version`, raw path, source fingerprint, `artifact_prefix`, `created_at`, and `updated_at`.
- `## Artifact References`: source, parsed statement, process artifact, categorize artifact, write or validation references, memory handoff references, and the matching status key.
- `## Questions`: import-owned questions in full; stage-owned questions only as ids, source artifact paths, and import-level resume decisions.
- `## First-Seen Account Decisions`: proposed, approved, rejected, or written account-opening decisions with evidence, target files, validation, and approval context.
- `## Document Reference Decisions`: proposed, approved, reused, rejected, blocked, or written raw-statement `document` directives with account, date, path, target file, duplicate check, validation, and approval context.
- `## Cross-Statement Review`: transfer or duplicate candidates spanning statements, with paired artifact paths, transaction refs, matched facts, decision state, and posting impact.
- `## Posting Decisions`: write inputs, write result references, validation references, blockers, and user approval context.
- `## Memory Attribution`: governed memory records considered or used, current-evidence checks, influenced decisions, and rejection reasons.
- `## Memory Candidates`: reusable-learning candidates with provenance, originating artifact path, review state, eligibility, and deduplication status.
- `## Ignored Or Rejected Inputs`: unsafe paths, stale references, invalid suggestions, unresolved blockers, or rejected memory candidates.

## Update Rules

- Persist every import-owned decision before asking the user for approval, handing work to another stage, invoking `$auto-bean-memory`, or marking the statement `done`.
- Update `updated_at` whenever a section changes.
- Link to stage-owned artifacts instead of copying their full warning, question, answer, parsing, categorization, or reconciliation detail.
- Store only summaries, paths, stable ids, evidence references, decisions, and compact validation results.
- Fail closed if the artifact path escapes `.auto-bean/artifacts/import/`, the prefix conflicts with sibling artifacts, the artifact cannot be read or updated, or references conflict with `statements/import-status.yml`.

## Do Not Store

- Workflow counts, queue position, retry counters, status transition logs, current status, highest status reached, or batch progress.
- Raw statement dumps, full parsed JSON payloads, complete ledgers, parser stdout/stderr, full memory files, or unrelated financial data.
- Stage-owned process or categorize narratives beyond the import decision or blocker that affects orchestration.
