# Auto Bean Ownership Map

Purpose: single reference for which stage owns each workflow surface.

## Stage Ownership

| surface | owner | notes |
| --- | --- | --- |
| Raw statement discovery | `$auto-bean-import` | Finds changed or unprocessed files under `statements/raw/`. |
| Raw-to-parsed processing | `$auto-bean-process` | Processes exactly one assigned raw statement. |
| Parsed statement evidence | `$auto-bean-process` | Writes normalized JSON under `statements/parsed/`. |
| Import status index | stage owner for its entry | Operational pointers and compact flags only. See `import-status-reading.md`. |
| Process artifact | `$auto-bean-process` | Processing warnings, questions, answers, manual extraction notes, and processing memory suggestions. |
| Import-owned artifact | `$auto-bean-import` | Statement-scoped provenance, import-owned decisions, brokered question ids, handoffs, and final-review references. |
| Categorize artifact | `$auto-bean-categorize` | Categorization, reconciliation, deduplication, fillable questions, answers, blockers, and memory suggestions. |
| Cross-statement review notes | `$auto-bean-import` | May append clearly labeled batch-review notes to categorize artifacts. |
| First-seen account structure during import | `$auto-bean-import` | Requires user approval before ledger mutation. |
| Transaction drafting | `$auto-bean-write` | Writes transaction entries and minimal transaction-supporting directives from trusted evidence. |
| Final import approval | `$auto-bean-import` | User-facing approval broker for import workflows. |
| Commit and push readiness | `$auto-bean-import` | Import-owned finalization boundary. |
| Workflow-specific JSON memory writes | `$auto-bean-memory` | Only this skill writes `.auto-bean/memory/*.json` and `.auto-bean/memory/import_sources/*.json`. |
| Global profile memory (`MEMORY.md`) | main-thread orchestrator or direct write session | `$auto-bean-import`, direct `$auto-bean-write`, and `$auto-bean-memory` may update `.auto-bean/memory/MEMORY.md` for durable user profile, preference, correction, and general workspace context. Sub-agents return suggestions only. |
| Ledger reads and analysis | `$auto-bean-query` | Read-only Beancount and BQL analysis. |

If a requested mutation is outside these owners, ask which workflow should own it instead of expanding a read-only or sub-agent skill.
