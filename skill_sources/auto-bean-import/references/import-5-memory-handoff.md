# Import Memory Handoff

Use after import parsing, categorization, writing, validation, and final-review context are available.

Use the shared conservative default here: the memory handoff is proactive only for governed, reversible, advisory memory writes that pass eligibility checks. It must not advance statement status, bypass user approval, or turn unresolved stage blockers into durable memory.

1. Collect workflow artifacts produced during the import:
   - process artifacts under `.auto-bean/artifacts/process/`
   - categorize artifacts under `.auto-bean/artifacts/categorize/`
   - statement-scoped import-owned artifacts under `.auto-bean/artifacts/import/`
2. Invoke `$auto-bean-memory` once:
   - pass eligible memory suggestions with provenance and current review state
   - do not call `$auto-bean-memory` separately for each artifact
   - invoke memory only after import-stage statements are either `done`, `final_review`, or intentionally blocked
   - keep memory handoff separate from statement status advancement
