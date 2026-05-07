# Import Memory Handoff

Use after import parsing, categorization, writing, validation, and final-review context are available.

- Collect workflow artifacts produced during the import:
  - process artifacts under `.auto-bean/artifacts/process/`
  - categorize artifacts under `.auto-bean/artifacts/categorize/`
  - statement-scoped import-owned artifacts under `.auto-bean/artifacts/import/`
- Spawn a single sub-agent that invokes `$auto-bean-memory` once with the artifact set, asking it to persist any reusable learning as governed memory for future import work.
- Do not call `$auto-bean-memory` separately for each artifact.
- Report the `$auto-bean-memory` result separately from import parsing, posting, validation, and final approval status.
- Gate: invoke memory only after import-stage statements are either `done`, `final_review`, or intentionally blocked; memory must not advance statement status.
