# Skill & Prompt Review Report (Detailed)

Scope reviewed:
- All Markdown files under `skill_sources/`
- `workspace_template/AGENTS.md`

Date: 2026-05-10

## Executive Summary

The prompt system is well-structured and safety-oriented, but there are meaningful quality risks in six areas:
1. Contradictions between global ownership rules and stage-level instructions.
2. Ambiguous language that leaves room for inconsistent execution.
3. Persona drift between strict/gated stages and proactive/autonomous stages.
4. High cognitive load from deep nested rules and repeated constraints.
5. Missing explicit error-path behavior for several realistic failures.
6. Composition conflicts where imported shared rules are weakened downstream.

Priority snapshot:
- **P0**: 2 issues (execution conflicts)
- **P1**: 7 issues (clarity, consistency, and reliability)
- **P2**: 8 issues (maintainability and long-term drift control)

---

## 1) Contradiction Detection

### [DONE] C-1 (P0) Memory ownership contradiction: who can write `.auto-bean/memory/**` 

**Concerned files**
- `skill_sources/shared/workflow-rules.md`
- `skill_sources/auto-bean-import/SKILL.md`
- `skill_sources/auto-bean-write/SKILL.md`
- `workspace_template/AGENTS.md`

**Problem detail**
- Ownership map states: governed memory writes are owned by `$auto-bean-memory` and says “Only this skill writes `.auto-bean/memory/**`.”
- Import and write skills instruct main-thread session-end updates to `.auto-bean/memory/MEMORY.md`.
- Workspace template also mandates updating `MEMORY.md` before ending a main-thread session.

This creates a direct policy contradiction and can produce two failure modes:
- **Over-restriction**: Orchestrator refuses required session-end `MEMORY.md` update.
- **Over-permission**: Non-memory skills write JSON memory files beyond intended scope.

**Concrete example of the problem**
- During import finalization, `$auto-bean-import` reaches “End With” and attempts `MEMORY.md` update.
- A strict owner interpreter blocks the write because ownership map says only `$auto-bean-memory` writes under `.auto-bean/memory/**`.
- Session exits non-compliant with workspace policy.

**Suggested solution (recommended)**
1. Split ownership model into two rows in `workflow-rules.md`:
   - Workflow-specific JSON memory (`account_mappings.json`, `category_mappings.json`, etc.) -> only `$auto-bean-memory`.
   - Global profile memory (`MEMORY.md`) -> main-thread orchestrators (`$auto-bean-import`, direct `$auto-bean-write`) MAY update at session end; sub-agents MUST only suggest edits.
2. Keep `$auto-bean-memory` as canonical writer for governed JSON memory.
3. Add a short normative paragraph in `workflow-rules.md` to unify this behavior.

**Sample wording patch**
- “Only `$auto-bean-memory` writes workflow-specific JSON memory files under `.auto-bean/memory/*.json` and `.auto-bean/memory/import_sources/*.json`. `MEMORY.md` may be updated by main-thread orchestrator/write skills for end-of-session durable user context; import sub-agents return suggestions only.”

---

### [DONE] C-2 (P0) Sub-agent user-question rule is absolute in shared contract but softened in stage text

**Concerned files**
- `skill_sources/shared/question-handling-contract.md`
- `skill_sources/shared/workflow-rules.md`
- `skill_sources/auto-bean-categorize/SKILL.md`
- `skill_sources/auto-bean-process/SKILL.md`

**Problem detail**
- Shared contract is absolute: import-invoked sub-agent NEVER asks the user directly.
- Some stage guidance uses softer phrasing (e.g., “normally return question ids...”), which implies optionality.

**Concrete example of the problem**
- A categorization ambiguity appears.
- Stage text “normally return question ids” can be interpreted as “sometimes ask directly.”
- This bypasses `$auto-bean-import` broker ownership and breaks consistent user interaction flow.

**Suggested solution**
- Replace all soft phrases with absolute language in import-invoked contexts:
  - “When invoked by `$auto-bean-import`, never ask the user directly; persist question in stage-owned artifact and return only ids/paths/flags.”
- Add lint-like editorial rule: downstream stage files cannot weaken shared contract modalities.

**Sample wording patch**
- Current (soft): “normally return question ids ...”
- Proposed (strict): “return question ids ... and never ask the user directly when import-invoked.”

---

## 2) Semantic Ambiguity (with rewrite suggestions)

### A-1 (P1) “Fail closed” lacks a canonical operational definition

**Concerned files**
- `skill_sources/shared/workflow-rules.md`
- `skill_sources/auto-bean-process/SKILL.md`
- `skill_sources/auto-bean-categorize/SKILL.md`
- `skill_sources/auto-bean-query/SKILL.md`
- `skill_sources/auto-bean-memory/SKILL.md`

**Problem detail**
“Fail closed” appears frequently but with uncertain action semantics (stop immediately vs persist safe progress first vs set blocked status vs return warning only).

**Example**
- Process stage sees ambiguous account_id in multi-account statement. One implementation stops without status mutation; another sets `process_blocked`; another emits warning and continues.

**Suggested solution**
Add a shared 4-step invariant in `workflow-rules.md`:
1. Persist deterministic safe progress.
2. Update stage status to blocked state when status model supports it.
3. Record blocker details in stage-owned artifact.
4. Return explicit blocker metadata and required input.

**Sample canonical text**
- “Fail closed = no guessing; persist safe progress; set blocked status when available; write blocker details to owning artifact; return explicit blocker/resume requirements.”

---

### A-2 (P1) “Read when needed” trigger thresholds are underspecified

**Concerned files**
- `skill_sources/auto-bean-query/SKILL.md`
- `skill_sources/auto-bean-process/SKILL.md`
- `skill_sources/auto-bean-categorize/SKILL.md`
- `skill_sources/shared/memory-access-rules.md`

**Problem detail**
“when needed / when unclear” relies on agent judgment but lacks deterministic trigger points.

**Example**
- Query stage computes period report but does not consult BQL window semantics because “unclear” was interpreted too narrowly.

**Suggested solution**
- Add explicit trigger table per skill:
  - If using OPEN/CLOSE semantics -> MUST open `bean-query-patterns.md` section on reporting windows.
  - If using memory-derived category suggestion -> MUST execute memory gating checklist from shared memory rules.
  - If multi-account parsed file and `account_id` mismatch appears -> MUST open parsed-statement reading guidance before continuing.

---

### A-3 (P1) Optional categorize artifact can reduce audit continuity

**Concerned files**
- `skill_sources/auto-bean-categorize/SKILL.md`
- `skill_sources/auto-bean-import/references/import-3-categorization-review.md`

**Problem detail**
Current guidance allows returning without categorize artifact for trivial no-blocker work, which can fragment the review trail.

**Example**
- Statement A has “trivial” categorization with no artifact.
- Later cross-statement duplicate with statement B requires evidence chain, but A has no persistent categorized reasoning surface.

**Suggested solution**
- Require always-on categorize artifact.
- Permit a “short-form” artifact template for trivial cases (summary, confidence, no blockers, no questions).

**Sample short-form template**
- Header metadata
- Categorized count + confidence
- Findings: none
- Questions: none
- Memory suggestions: none

---

### A-4 (P2) Memory relevance criteria are dispersed and unevenly phrased

**Concerned files**
- `skill_sources/shared/memory-access-rules.md`
- `skill_sources/auto-bean-categorize/SKILL.md`
- `skill_sources/auto-bean-process/SKILL.md`
- `skill_sources/auto-bean-memory/SKILL.md`

**Problem detail**
Skills reference relevance/confidence in different wording, increasing interpretation drift.

**Suggested solution**
- Add a canonical 5-question gating checklist in `memory-access-rules.md`, referenced by all skills:
  1. Is source identity match strong and current?
  2. Is scope match exact enough?
  3. Are at least two independent current facts aligned?
  4. Is reuse risk low and reversible?
  5. Is audit provenance available?

---

### A-5 (P2) “Minimal supporting directives” in write skill may be interpreted too broadly

**Concerned file**
- `skill_sources/auto-bean-write/SKILL.md`

**Problem detail**
Without explicit bounds, this can expand into structural ledger edits not necessary for a transaction.

**Example**
- Agent adds new include graph file and reorganizes account tree “to support” one transaction.

**Suggested solution**
- Define an explicit allowlist:
  - Allowed by default: transaction entries; minimal `open` needed for target account; narrowly scoped `balance` when required for integrity.
  - Require explicit user approval for anything beyond allowlist (e.g., include graph reorganization).

---

## 3) Persona Consistency (tone/behavior)

### P-1 (P1) Conservative workflow persona vs proactive memory persona

**Concerned files**
- `skill_sources/shared/workflow-rules.md`
- `skill_sources/auto-bean-memory/SKILL.md`
- `skill_sources/auto-bean-import/SKILL.md`

**Problem detail**
Most docs emphasize conservative, blocker-aware gating; memory skill encourages autonomous persistence when eligible.

**Risk**
Users may perceive inconsistent agent behavior across stages (hesitant in one stage, assertive in another) without clear rationale.

**Suggested solution**
- Add shared persona paragraph:
  - “Default posture is conservative and evidence-first.
  - Proactive action is allowed only for governed, reversible memory writes passing eligibility checks.”

**Example alignment outcome**
- Import stage remains approval-gated for ledger writes.
- Memory stage may autonomously write eligible reusable mapping with explicit post-write disclosure.

---

### P-2 (P2) Modality inconsistency (`MUST`, `Always`, `Prefer`, `Normally`)

**Concerned files**
- All `skill_sources/**.md` stage/shared files

**Problem detail**
Mixed modal verbs reduce deterministic interpretation and make contract-strength unclear.

**Suggested solution**
- Normalize modality taxonomy globally:
  - MUST = hard invariant
  - SHOULD = preferred default with documented exception
  - MAY = optional
- Editorial pass across stage and reference docs.

---

## 4) Cognitive Load Assessment

### [DONE] L-1 (P1) Deep nested constraints in process/categorize/import/write raise execution error risk

**Concerned files**
- `skill_sources/auto-bean-process/SKILL.md`
- `skill_sources/auto-bean-categorize/SKILL.md`
- `skill_sources/auto-bean-import/SKILL.md`
- `skill_sources/auto-bean-import/references/import-*.md`
- `skill_sources/auto-bean-write/SKILL.md`

**Problem detail**
Long instruction ladders with many conditional branches are robust but hard to execute consistently in one pass.

**Example**
- Process stage combines source validation, fingerprinting, memory lookup, CLI extraction, normalization, status updates, retries, and artifact conventions. Missing one sub-step can silently desynchronize status/artifact state.

**Suggested solution**
- Add “Fast Path Checklist” at top of each stage file (8–12 bullets).
- Keep detailed logic below as reference.
- Add completion checklist with mandatory outputs (status mutation, artifact path, return schema fields).

---

### L-2 (P2) Repeated policy text creates drift risk

**Concerned files**
- `skill_sources/shared/*.md`
- `skill_sources/*/SKILL.md`

**Problem detail**
Similar rules (question broker, memory advisory nature, status payload boundaries) appear in several places with slight wording changes.

**Suggested solution**
- Centralize canonical policy paragraphs in shared docs.
- In stage docs, link by anchor and avoid rephrasing hard invariants.

---

### L-3 (P2) Import reference sequencing is correct but mentally heavy

**Concerned files**
- `skill_sources/auto-bean-import/SKILL.md`
- `skill_sources/auto-bean-import/references/import-1-discovery.md`
- `skill_sources/auto-bean-import/references/import-2-account-inspection.md`
- `skill_sources/auto-bean-import/references/import-3-categorization-review.md`
- `skill_sources/auto-bean-import/references/import-4-write-final-review.md`
- `skill_sources/auto-bean-import/references/import-5-memory-handoff.md`

**Suggested solution**
- Add one dependency matrix table:
  - Stage -> required files -> optional files -> gate conditions -> outputs.

**Example table row**
- Stage 3 categorization review -> required: import-3 + ownership map + question contract -> gate: all statements at categorize_review or resolved blockers -> outputs: import artifact updates + write handoff inputs.

---

## 5) Semantic Coverage Gaps

### S-1 (P1) Missing explicit timeout/retry taxonomy for external tooling

**Concerned file**
- `skill_sources/auto-bean-process/SKILL.md`

**Problem detail**
Docling command guidance is good, but timeout, retry classes, and failover thresholds are not explicit.

**Example**
- Docling hangs on a malformed PDF; no standardized timeout means inconsistent behavior.

**Suggested solution**
- Add command policy:
  - Timeout per file type (e.g., PDF 120s, CSV/XLSX 60s).
  - Retry limits by failure class (transient IO vs parser crash vs format unsupported).
  - Deterministic mapping to `process_blocked` reasons.

---

### S-2 (P1) Malformed artifact repair flow not explicit enough

**Concerned files**
- `skill_sources/auto-bean-import/references/import-artifact-contract.md`
- `skill_sources/shared/workflow-rules.md`

**Problem detail**
Missing clear steps for partially corrupted markdown artifacts or malformed JSON memory records.

**Suggested solution**
- Add repair protocol:
  1. Preserve original file.
  2. Append `## Recovery Notes` with timestamp and issue.
  3. Restore minimum required sections.
  4. Mark unresolved ambiguity as blocker.

---

### S-3 (P2) Status vs artifact divergence resolution lacks tie-break hierarchy

**Concerned files**
- `skill_sources/shared/import-status-reading.md`
- `skill_sources/auto-bean-import/references/import-artifact-contract.md`
- `skill_sources/auto-bean-import/SKILL.md`

**Problem detail**
References mention boundaries but not one canonical precedence order for conflict resolution.

**Example**
- Status points to parsed artifact A, import artifact references parsed artifact B.

**Suggested solution**
- Define precedence and reconciliation:
  1. Existing source file/fingerprint reality
  2. Status entry operational pointers
  3. Artifact references
  4. If unresolved, block and ask user-brokered clarification.

---

### S-4 (P2) Query-stage non-BQL escalation path is underdefined

**Concerned file**
- `skill_sources/auto-bean-query/SKILL.md`

**Problem detail**
Read-only scope is clear, but escalation when BQL cannot answer safely (complex valuation edge cases) is not explicit.

**Suggested solution**
- Add “cannot answer safely in BQL” branch:
  - explain limitation
  - offer closest safe query
  - route mutation/advanced valuation decisions to appropriate workflow

---

## 6) Composition Conflict Analysis (linked/imported prompt interactions)

### X-1 (P1) Downstream files occasionally weaken imported shared constraints

**Concerned files**
- Shared contract: `skill_sources/shared/question-handling-contract.md`
- Downstream stage skills where wording is softer

**Problem detail**
Imported contract says NEVER; downstream language sometimes says normally/usually.

**Suggested solution**
- Add authoring rule in shared docs:
  - “Stage files may specialize but not weaken shared invariants.”
- Add CI lint check for forbidden weakening phrases in import-invoked sections.

**Example lint rule**
- If section contains “import-invoked”, forbid `normally`, `usually`, `try to` around user-ask policy.

---

### X-2 (P2) Ownership-map breadth conflicts with stage end-of-session memory behaviors

**Concerned files**
- `skill_sources/shared/workflow-rules.md`
- `skill_sources/auto-bean-import/SKILL.md`
- `skill_sources/auto-bean-write/SKILL.md`
- `workspace_template/AGENTS.md`

**Suggested solution**
- Decompose ownership statement into separate rows for JSON memory vs `MEMORY.md` (as in C-1).

---

### X-3 (P2) Import artifact boundaries vs stage return richness can still drift

**Concerned files**
- `skill_sources/auto-bean-import/references/import-artifact-contract.md`
- `skill_sources/shared/workflow-rules.md`

**Problem detail**
Return schemas may include rich detail; import artifact contract restricts copying full stage payloads.

**Suggested solution**
- Add explicit examples of:
  - Allowed in import artifact: ids, paths, compact decision summary.
  - Forbidden: full question text copied from categorize/process artifacts.

**Example**
- Allowed: `question_id: cat-q-014, source_artifact: .../x--categorize.md, decision: pending`.
- Forbidden: full 20-line reconciliation question body duplicated into import artifact.

---

## Prioritized Improvement Plan

## P0 (Immediate)
1. Resolve memory write ownership contradiction between ownership map and stage/workspace requirements.
2. Standardize absolute “never ask user directly” wording for import-invoked sub-agents in all stage files.

## P1 (Next sprint)
3. Add canonical “fail closed” operational steps in shared workflow rules.
4. Add deterministic “read when needed” trigger tables in query/process/categorize.
5. Require always-on categorize artifact with short-form template option.
6. Add timeout/retry/error taxonomy for docling execution.
7. Add malformed artifact repair protocol.
8. Add shared persona statement clarifying conservative default vs governed proactive memory writes.
9. Add fast-path checklists and completion checklists to process/categorize/import.

## P2 (Backlog)
10. Normalize modality taxonomy (MUST/SHOULD/MAY) across all markdown prompts.
11. Reduce repeated policy text by linking canonical shared anchors.
12. Add status/artifact divergence precedence and reconciliation procedure.
13. Add query non-BQL escalation branch guidance.
14. Add composition examples for allowed/forbidden import-artifact detail.
15. Add authoring/lint rules that prevent weakening shared invariants in downstream files.
16. Add import stage dependency matrix for cognitive load reduction.
17. Add shared memory gating checklist IDs and required usage points.

---

## Suggested Implementation Sequence

1. **Shared policy pass**
   - Update `skill_sources/shared/workflow-rules.md`, `question-handling-contract.md`, `memory-access-rules.md`.
2. **Stage alignment pass**
   - Align `auto-bean-process`, `auto-bean-categorize`, `auto-bean-import`, `auto-bean-write`, `auto-bean-query`, `auto-bean-memory` language to shared invariants.
3. **Reference contract pass**
   - Update import reference docs and return examples with explicit allowed/forbidden composition examples.
4. **Quality guard pass**
   - Add lightweight lint/editorial checks for modal consistency and weakening phrases.

This order resolves hard contradictions first, then ambiguity, then maintainability.
