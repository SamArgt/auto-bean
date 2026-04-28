# Reading Import Status

`statements/import-status.yml` is the operational index for import work. Each entry is keyed by raw statement path and should stay small: current status, source fingerprint, parsed statement path, stage artifact paths, timestamps, retry hold metadata, and compact booleans such as whether user input is required.

When the file is large:

- Search by exact raw path first, then read only that entry.
- Use `rg -n "statements/raw/...|current_status:|parsed_statement:|artifacts:" statements/import-status.yml` to find nearby lines quickly.
- Use a YAML parser for edits or audits; avoid broad text rewrites that could move unrelated statement entries.
- Treat `parsed_statement` as evidence under `statements/parsed/`, not a workflow artifact.
- Treat `artifacts.process`, `artifacts.categorize`, and `artifacts.import` as pointers to stage-owned review/provenance files under `.auto-bean/artifacts/`.
- Read warnings, blockers, questions, answers, categorization notes, and posting decisions from the referenced individual stage artifacts, not from the status entry or parsed statement.
- Do not store warning text, question text, answer text, or decision rationale in `statements/import-status.yml`; store only the artifact pointer and any compact operational flag needed for orchestration.
