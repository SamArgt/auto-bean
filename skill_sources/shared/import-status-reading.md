# Reading Import Status

`statements/import-status.yml` is the operational index for import work. Each entry is keyed by raw statement path and should stay small: current status, source fingerprint, parsed statement path, stage artifact paths, timestamps, and retry hold metadata.

When the file is large:

- Search by exact raw path first, then read only that entry.
- Use `rg -n "statements/raw/...|current_status:|parsed_statement:|artifacts:" statements/import-status.yml` to find nearby lines quickly.
- Use a YAML parser for edits or audits; avoid broad text rewrites that could move unrelated statement entries.
- Treat `parsed_statement` as evidence under `statements/parsed/`, not a workflow artifact.
- Treat `artifacts.process`, `artifacts.categorize`, and `artifacts.import` as pointers to stage-owned review/provenance files under `.auto-bean/artifacts/`.
- Read detailed warnings, blockers, questions, categorization notes, and posting decisions from the referenced stage artifacts, not from the status entry or parsed statement.
