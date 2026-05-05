# Skill Sources Review Report (Follow-up)

Date: 2026-04-29  
Scope: `skill_sources/**` with focus on simplification, clarity, shared-reference quality, and context-window efficiency.

## What I reviewed

- Prior report: `_dev-output/skills-review-report.md`.
- All skill definitions:
  - `skill_sources/auto-bean-import/SKILL.md`
  - `skill_sources/auto-bean-process/SKILL.md`
  - `skill_sources/auto-bean-categorize/SKILL.md`
  - `skill_sources/auto-bean-write/SKILL.md`
  - `skill_sources/auto-bean-query/SKILL.md`
  - `skill_sources/auto-bean-memory/SKILL.md`
- Shared references in `skill_sources/shared/*.md`.

---

## Direct answers to your questions

## 1) Shared references that are unnecessary or not truly shared

### A. `shared/beancount-syntax-and-best-practices.md` is useful, but contains non-shared workflow detail

This file is referenced by both `auto-bean-query` and `auto-bean-write`, so it *is* shared. But one bullet appears workflow-specific:

- "When operating inside `$auto-bean-categorize`, return only question ids and artifact path..."

That line is orchestration behavior, not Beancount syntax. It adds cognitive noise for skills that load the doc for ledger semantics.

**Suggestion:** split this doc into:
- **pure Beancount syntax/ledger safety** (kept shared), and
- **workflow interaction guidance** (moved to `question-handling-contract.md` or per-skill docs).

### B. `shared/import-status.example.yml` appears under-used as an active dependency

`auto-bean-import` and `auto-bean-process` list it in "Read before proceeding". In practice, most operational guidance is already in `shared/import-status-reading.md`.

**Suggestion:** either:
- keep only one compact schema example embedded in `import-status-reading.md`, or
- keep `import-status.example.yml` but remove it from mandatory pre-read list and reference it "only when creating new fields".

### C. `shared/parsed-statement-output.example.json` is borderline optional for categorize

`auto-bean-process` clearly benefits from this as output contract guidance. `auto-bean-categorize` may only need field-level expectations, which are also discoverable via `parsed-statement-jq-reading.md`.

**Suggestion:** keep shared file, but in categorize make it conditional ("read when parsed shape is unclear") rather than unconditional in the pre-read block.

---

## 2) Repetitive statements

There is still meaningful repetition across skills despite previous cleanup.

### A. Repeated question-handling language

`auto-bean-import`, `process`, `categorize`, and `write` all repeat variants of:
- persist safe progress first,
- record question in artifact,
- return question ids + artifact path to import when import-invoked.

Since `shared/question-handling-contract.md` already centralizes this, repeated long-form copies in each `SKILL.md` can be reduced.

**Suggestion:** replace repeated paragraphs with a short pointer:
- "Follow shared question-handling contract; only list stage-specific exceptions here."

### B. Repeated memory fail-closed language

`shared/memory-access-rules.md` is comprehensive, but skills still restate many of the same constraints.

**Suggestion:** keep one 1–2 line local reminder per skill and remove duplicated detailed clauses, unless a skill has a unique exception.

### C. "Read before proceeding" blocks are heavy and front-loaded

Some skills require 6–8 docs before step 1. This can bloat context and reduce execution focus.

**Suggestion:** split into:
- **always-read (max 2–3 docs)**
- **read-when-needed** by condition (large JSON, ambiguous clarification, reconciliation finding types, etc.)

---

## 3) Non-critical statements that can bloat context or confuse

### A. Excessive universal admonitions in shared docs

Several shared docs include repeated safety caveats that are already system-level policy in the skills. Good for safety, but verbose.

**Suggestion:** compress recurring admonitions into a "Safety baseline" section reused by link, then keep each file focused on operational specifics.

### B. Mixed concerns inside shared docs

Example: Beancount syntax doc includes cross-skill collaboration instructions; parsed statement jq doc includes artifact ownership reminders. These are valid, but can dilute the main "how-to" purpose.

**Suggestion:** keep each shared doc single-purpose:
- syntax doc = ledger constructs only
- jq doc = extraction/querying patterns only
- orchestration behaviors = question-handling/import-status docs.

### C. Similar "do not store X in import-status" guidance appears in multiple places

This rule already appears clearly in `import-status-reading.md` and `question-handling-contract.md`.

**Suggestion:** retain canonical wording in one place, and in other files reference it briefly.

---

## Practical simplification plan (low risk)

1. **Refactor pre-read sections** in each skill to "Always vs Conditional".  
2. **Move non-syntax workflow bullets out of `beancount-syntax-and-best-practices.md`**.  
3. **Keep one canonical source for question persistence rules** and remove duplicated prose in per-skill workflow steps.  
4. **Demote `import-status.example.yml` from mandatory read** unless schema changes are being made.  
5. **Add short "why this doc exists" header to each shared reference** to reduce accidental overloading.

---

## Net assessment

- The architecture is strong and mostly coherent.
- Biggest remaining opportunity is **instruction compression without losing safeguards**.
- You can likely reduce loaded token volume per run by ~20–35% by tightening pre-read lists and removing cross-file repeated policy text, while preserving behavior.

---

## Additional recommendations for `workspace_template/AGENTS.md`

### 1) Split into "Quick Start" vs "Deep Policy"

The current file is clear but dense. New sessions would benefit from a short front section with:
- when to use each core skill,
- import entry command,
- finalization boundary.

Keep detailed status semantics and guardrails in a second section. This reduces first-turn context load while preserving full policy.

### 2) Convert long import status prose into a compact table

The status list is accurate but verbose for repeated reading.

**Suggestion:** represent statuses as a 3-column table:
- `status`
- `owner next action`
- `blocked by`

This improves scan speed and reduces interpretation drift for orchestrator behavior.

### 3) Centralize repeated "persist safe progress before asking" language by reference

`workspace_template/AGENTS.md` repeats a longer variant of the same question-handling rule already formalized in `shared/question-handling-contract.md`.

**Suggestion:** keep a short local reminder and link to the shared contract to avoid policy divergence.

### 4) Clarify commit/push authority with one explicit sentence

The review boundary is good, but adding one canonical sentence helps:
- "For import workflows, `$auto-bean-import` is the sole broker for final user approval and commit/push readiness."

This avoids overlap interpretation with write-stage responsibilities.

### 5) Move path catalog lower and keep only high-frequency paths up top

The full path list is useful as reference, but it occupies prime context space.

**Suggestion:** keep 4–5 high-frequency paths near the top (`ledger.beancount`, `beancount/`, `statements/raw`, `statements/parsed`, `import-status`) and move the rest under a "Reference Paths" subsection.

### 6) Tighten guardrails to avoid negative-only phrasing overload

Guardrails are important, but multiple "Do not..." lines in sequence can reduce readability.

**Suggestion:** reframe as short "Always / Never" bullets:
- Always validate before finalization.
- Always route reads/writes through foundation skills.
- Never treat unapproved working tree changes as finalized.

This keeps strictness while improving fast comprehension.
