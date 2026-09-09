# Import Memory Handoff

Use after import parsing, categorization, writing, validation, and final-review context are available.

Use the shared conservative default here: the memory handoff is proactive only for governed, reversible, advisory memory writes that pass eligibility checks. It must not advance statement status, bypass user approval, or turn unresolved stage blockers into durable memory.

1. Collect workflow artifacts produced during the import:
   - process artifacts under `.auto-bean/artifacts/process/`
   - categorize artifacts under `.auto-bean/artifacts/categorize/`
   - statement-scoped import-owned artifacts under `.auto-bean/artifacts/import/`
   - other relevant context such as ledger excerpts, user-provided evidence and prices update results
2. Invoke `$auto-bean-memory` once:
   - pass eligible memory suggestions with provenance and current review state
   - do not call `$auto-bean-memory` separately for each artifact
   - invoke memory after safe work for the current invocation and any price epilogue have returned; statements awaiting input or approval retain their existing statuses
   - keep memory handoff separate from statement status advancement
