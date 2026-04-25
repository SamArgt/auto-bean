# Skill Sources Review Report

Date: 2026-04-25
Reviewer: Codex
Scope: All authored skills under `skill_sources/*/SKILL.md` and their interface metadata under `skill_sources/*/agents/openai.yaml`.

## Executive summary

- The overall architecture is coherent: `auto-bean-import` orchestrates, `auto-bean-process` handles raw-to-parsed conversion, `auto-bean-categorize` handles categorization/reconciliation, `auto-bean-write` performs ledger mutation, `auto-bean-query` is read-only analysis, and `auto-bean-memory` governs durable memory.
- Cross-skill boundaries are mostly explicit and conservative (fail-closed behavior, no silent guessing, no direct memory writes outside `$auto-bean-memory`).
- The biggest quality risks are not major contradictions, but **instruction density/repetition**, a few **ownership ambiguities**, and one likely **workflow loop risk** around `ready` status reprocessing.

---

## 1) Individual skill review

### 1.1 `auto-bean-import`

**Strengths**
- Clear top-level orchestration and lifecycle from discovery to `done`.
- Explicit stage transitions (`parsed*` -> `account_inspection` -> `ready_for_categorization` -> `ready_for_review` -> `ready_to_write` -> `final_review` -> `done`).
- Explicit downstream ownership boundaries for process/categorize/write/memory.

**Findings**
- **Potential loop ambiguity on `ready`:** discovery says to send files to process when status is `ready`; process sets `ready` when trustworthy parsed evidence is not available. Without additional gate conditions, this can cause repeated reprocessing attempts for permanently blocked files (e.g., scanned PDFs) rather than surfacing durable manual-resolution status.
- **Commit/push ownership unclear:** import ends with readiness for final approval, commit, or push, while write skill also demands explicit approval before commit/push. The owner of commit/push finalization (import vs write vs calling agent) is not fully singular.
- **High repetition:** many bullets restate “persist safe progress before asking user input,” which is correct but repeated heavily across steps.

**Clarity opportunities**
- Add one explicit anti-loop rule for repeated `ready` failures (e.g., bounded retry + manual queue marker).
- Clarify single owner for commit/push when workflow is invoked via import.
- Require `auto-bean-import` to persist one global import artifact that summarizes overall workflow state plus import-owned decisions (for example first-seen account derivations, process-question resolutions, posting handoff state, and final-review readiness) so downstream governance, including `$auto-bean-memory`, has a single audit surface.

### 1.2 `auto-bean-process`

**Strengths**
- Excellent scoping: single assigned raw statement only.
- Strong parse contract language and deterministic artifact expectations.
- Properly refuses to ask user directly and returns process artifacts to import.

**Findings**
- **Dependency assumption risk:** workflow mandates `./.venv/bin/docling` direct invocation; environments lacking this exact path may fail despite otherwise-valid tooling setups.
- **Status semantics depend on orchestrator behavior:** when process sets `ready` for untrustworthy parse, import must handle it carefully to avoid thrash.

**Clarity opportunities**
- Add fallback guidance for docling path/environment discovery (without weakening deterministic behavior).

### 1.3 `auto-bean-categorize`

**Strengths**
- Strong boundary discipline: assigned artifact only, no orchestration, no ledger writes.
- Good distinction between safe progress vs unresolved ambiguity.
- Clear reconciliation finding taxonomy (`likely_transfer`, `possible_duplicate`, `unbalanced`, `currency_risk`, `possible_future_transfer`).

**Findings**
- **Heavy payload requirement:** required return bundle is large (artifacts, posting inputs, findings, status metadata, pending questions, memory suggestions/files). This is comprehensive but may burden sub-agent implementations.
- **Potential duplication with import’s question handling language:** both skills heavily specify how user questions are persisted/surfaced.

**Clarity opportunities**
- Define a minimal required response schema and an optional extended schema to reduce variability.

### 1.4 `auto-bean-write`

**Strengths**
- Clear transaction-writing safety model (evidence first, bounded clarifications, validation required).
- Explicit integration behavior when called by import (return questions to caller, do not directly branch thread).

**Findings**
- **Potential ownership overlap with import on finalization:** write asks for explicit approval before commit/push; import also owns final review and done transitions. The commit/push boundary is present but not fully centralized.
- **Scope wording includes updates and minimal supporting directives;** still safe, but some teams may interpret this as broader than strictly transaction entries.

**Clarity opportunities**
- Add one sentence: when invoked by import, write never owns commit/push and only returns mutation + validation package.

### 1.5 `auto-bean-query`

**Strengths**
- Clean read-only boundary and excellent audit-friendly output guidance.
- Good caveat handling for inventory semantics and empty results.

**Findings**
- No major inconsistencies found.

**Clarity opportunities**
- Optionally note when shell command should prefer local venv path (`./.venv/bin/bean-query`) if PATH is unreliable.

### 1.6 `auto-bean-memory`

**Strengths**
- Strong governance model: separate read-only inspection, explicit correction/refinement/removal path, and governed persistence path.
- Excellent fail-closed language and fixed-file map.

**Findings**
- **Minor wording defect:** repeated phrase in inspection step 1 (“before inspecting runtime memory” appears twice).
- **Instruction volume is very high:** three dense workflows can be hard to execute consistently without structured checklist output.

**Clarity opportunities**
- Reduce duplication by extracting shared validation checks once and referencing them in each workflow.

---

## 2) Scope and interaction mapping

### 2.1 Responsibility map

| Skill | Primary scope | Writes ledger? | Writes memory? | Asks user directly? | Typical invoker |
|---|---|---:|---:|---:|---|
| `auto-bean-import` | End-to-end orchestration of import lifecycle | Yes (first-seen account directives) and delegates postings | No | Yes | User/main thread |
| `auto-bean-process` | One raw statement -> normalized parsed artifact | No | No | No | `auto-bean-import` |
| `auto-bean-categorize` | One parsed/intermediate artifact categorization + reconciliation/dedupe findings | No | No | Normally no (returns Qs to import) | `auto-bean-import` |
| `auto-bean-write` | Draft/review/write transactions + validation | Yes | No | Yes if direct; no if import-invoked | `auto-bean-import` or direct user |
| `auto-bean-query` | Read-only ledger analysis via BQL | No | No | N/A | Any skill/user |
| `auto-bean-memory` | Governed memory inspection/correction/persistence | No | Yes (only allowed writer) | Yes when clarification needed | `auto-bean-import` or user |

### 2.2 Interaction graph (intended)

1. `auto-bean-import` discovers and dispatches raw files -> `auto-bean-process`.
2. `auto-bean-process` returns parsed artifacts/status/questions/memory suggestions -> `auto-bean-import`.
3. `auto-bean-import` resolves process questions, performs first-seen account work, then hands parsed items -> `auto-bean-categorize`.
4. `auto-bean-categorize` returns categorizations/findings/questions/posting inputs/memory suggestions -> `auto-bean-import`.
5. `auto-bean-import` resolves user input and dispatches posting -> `auto-bean-write`.
6. `auto-bean-write` returns written changes + validation (+clarification loop if needed) -> `auto-bean-import`.
7. `auto-bean-import` gathers approved reusable learnings -> `auto-bean-memory`.
8. `auto-bean-memory` persists governed memory and returns persistence summary -> `auto-bean-import`.

### 2.3 Shared artifacts/data ownership

- `statements/raw/*`: import/process input, never mutated by downstream stages.
- `statements/parsed/*`: produced by process, consumed by import/categorize/write.
- `statements/import-status.yml`: orchestrated by import; stage workers only update assigned scope.
- `.auto-bean/artifacts/process/*`: owned by process for question artifacts; surfaced by import.
- `.auto-bean/artifacts/categorize/*`: owned by categorize for review/question artifacts; surfaced by import.
- `.auto-bean/tmp/memory-suggestions/*`: temporary handoff from process/categorize, consolidated by import.
- `.auto-bean/memory/*`: writable only by memory skill.
- `.auto-bean/artifacts/import/*` (recommended): global import-owned audit artifact, produced and maintained by import, summarizing cross-statement progress, import-owned decisions, and memory-handoff context.

---

## 3) Cross-skill inconsistencies, unclear ownership, and repetition

### 3.1 Inconsistencies / tension points

1. **`ready` status reprocessing risk**
   - Process can set `ready` when parsing is untrustworthy.
   - Import discovery rule resends `ready` items to process.
   - Without additional stop condition, same source may loop indefinitely.

2. **Commit/push finalization ownership split**
   - Write includes explicit commit/push approval boundary.
   - Import owns final review + done and also mentions readiness for commit/push.
   - A single authoritative owner is implied but not explicitly fixed in all invocation modes.

3. **Path mental model mismatch for contributors**
   - Skill text references runtime paths under `.agents/skills/...` (valid for installed skills), while authoring source lives under `skill_sources/...`.
   - This is expected architecture-wise but can be confusing during repo-only reviews if not called out in contributor docs.

### 3.2 Unclear ownership areas

1. **First-seen account directives vs transaction posting**
   - Import writes account-opening directives; write handles transaction entries.
   - Boundary is reasonable but could be misunderstood as two mutation authorities unless summarized in one cross-skill policy block.

2. **User question channel ownership during nested calls**
   - Categorize and write both include “return question to import when import-invoked.”
   - Works in principle; still worth centralizing in import as single “user-interaction broker” rule.

### 3.3 Repetition hotspots

- “Persist all safe progress before asking the user” appears in import/process/categorize/write variants repeatedly.
- Memory advisory/fail-closed language appears in each skill plus shared rules (appropriate but verbose).
- Artifact path safety checks are repeated in multiple stages; a shared reusable checklist could reduce drift.

---

## 4) Recommended improvements (prioritized)

1. **Add anti-loop rule for `ready`** DONE
   - Introduce bounded retry metadata (e.g., retry count + last failure reason) and require import to stop automatic reprocess after threshold, surfacing manual-resolution requirement.

2. **Centralize commit/push authority statement** DONE
   - Add one unambiguous rule in import: commit/push is always orchestrator-owned; write never finalizes when invoked by import.

3. **Create shared “question-handling contract” snippet** DONE
   - Put common guidance in shared reference and link from process/categorize/write/import to reduce duplication.

4. **Add a global import-owned artifact contract**
   - Require `auto-bean-import` to maintain a deterministic artifact (for example under `.auto-bean/artifacts/import/`) that records whole-import state, stage ownership boundaries, first-seen account decisions, unresolved/answered questions, posting-readiness transitions, and memory candidate provenance so `$auto-bean-memory` can consume governed context without re-deriving workflow history.

5. **Create shared “memory suggestion envelope schema”**
   - Define required keys once, then reference from process/categorize/import.

6. **Add contributor note for source vs installed skill paths**
   - Explain that `skill_sources/` authoring material is rendered/installed to `.agents/skills/...` in workspace.

7. **Tighten minor wording defects**
   - Fix duplicated phrase in `auto-bean-memory` inspection workflow step 1.

---

## 5) Suggested ownership model (canonical)

- **Single user-facing broker:** `auto-bean-import` for import workflows.
- **Single raw parser worker:** `auto-bean-process`.
- **Single categorization/reconciliation worker:** `auto-bean-categorize`.
- **Single transaction mutation worker:** `auto-bean-write`.
- **Single durable memory writer:** `auto-bean-memory`.
- **Single read-only ledger query tool:** `auto-bean-query`.

This model already exists implicitly; the main recommendation is to make the boundary language shorter and even more explicit to reduce interpretation drift.
