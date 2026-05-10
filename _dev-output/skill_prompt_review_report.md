# Skill & Prompt Review Report

Scope reviewed:
- All Markdown files under `skill_sources/`
- `workspace_template/AGENTS.md`

Date: 2026-05-10

## Executive Summary

Overall quality is high: ownership boundaries, artifact contracts, and safety posture are unusually strong. The main risks are **instruction density**, a few **wording contradictions/edge ambiguities**, and **cross-file norm drift** where one file is stricter than another for similar behavior.

Priority snapshot:
- **P0**: 2 issues (must fix to avoid execution conflicts)
- **P1**: 5 issues (high-impact clarity and consistency)
- **P2**: 6 issues (usability and maintainability)

---

## 1) Contradiction Detection

### C-1 (P0) Memory ownership conflict: import/main-thread updates vs memory-only writer
**Where**
- `workspace_template/AGENTS.md` says to update `.auto-bean/memory/MEMORY.md` before ending every main-thread session.
- `skill_sources/shared/ownership-map.md` says only `$auto-bean-memory` writes `.auto-bean/memory/**`.
- `skill_sources/auto-bean-import/SKILL.md` and `skill_sources/auto-bean-write/SKILL.md` instruct main-thread updates to `MEMORY.md`.

**Conflict**
- “Only memory skill writes `.auto-bean/memory/**`” conflicts with import/write explicit instructions to update `MEMORY.md` directly.

**Recommendation**
- Amend ownership map to: “Only `$auto-bean-memory` writes workflow-specific JSON memory; `MEMORY.md` may be updated by main-thread orchestrator/write skills per session-end policy.”
- Or require import/write to call `$auto-bean-memory` for all memory writes (including `MEMORY.md`).

---

### C-2 (P0) Sub-agent user question behavior wording inconsistency
**Where**
- `skill_sources/shared/workflow-rules.md`: sub-agent handoff says sub-agents should not ask for clarification from user.
- `skill_sources/shared/question-handling-contract.md`: import-invoked broker rule says sub-agent NEVER asks user directly.
- Some stage skills use softer language: “normally return question ids...” rather than absolute prohibition.

**Conflict**
- Absolute contract exists, but some stage text implies optionality.

**Recommendation**
- Standardize all import-sub-agent skills to absolute wording: “Never ask user directly when import-invoked.”

---

## 2) Semantic Ambiguity + Rewrite Suggestions

### A-1 (P1) “Fail closed” is not operationally standardized
**Issue**
- Appears in many files, but exact action differs by stage (set blocked? return warning? stop without status mutation?).

**Rewrite snippet**
- Add shared definition in `workflow-rules.md`:
  - “Fail closed means: (1) persist safe progress, (2) set stage blocked status if applicable, (3) record blocker in stage-owned artifact, (4) return explicit blocker metadata; never fabricate missing facts.”

### A-2 (P1) “Read when needed” thresholds are subjective
**Issue**
- Triggers like “when unclear” are helpful but can vary widely by agent.

**Rewrite snippet**
- Add deterministic triggers (e.g., “if query needs OPEN/CLOSE windows, must open bean-query-patterns section X”).

### A-3 (P1) “Trivial no-blocker work may skip categorize artifact” can cause audit gaps
**Issue**
- Optional artifact creation in `auto-bean-categorize` may reduce traceability and cross-statement review continuity.

**Rewrite snippet**
- Require artifact always, but allow short form template for trivial cases.

### A-4 (P2) “Relevant memory hints” lacks a canonical filtering checklist
**Issue**
- Multiple skills reference relevance, confidence, and evidence checks differently.

**Rewrite snippet**
- Add a single 5-question gating checklist in `memory-access-rules.md` and reference by id.

### A-5 (P2) “Minimal transaction-supporting directives” may invite scope creep
**Issue**
- In write skill, “minimum supporting directives” could include broad account restructuring.

**Rewrite snippet**
- Define allowed directive list explicitly (e.g., `open`, `balance`, optional `pad`) and disallow others unless explicit approval.

---

## 3) Persona Consistency (Tone, Role, Behavioral Identity)

### P-1 (P1) Tone drift between “strict protocol” and “initiative/autonomy”
**Observation**
- Most skills emphasize conservative, gated behavior.
- `auto-bean-memory` encourages proactive autonomous persistence with no prior approval if eligible.

**Risk**
- Different “agent personalities” between stages may feel inconsistent and can surprise users.

**Recommendation**
- Add shared persona statement in `workflow-rules.md`: conservative by default; proactive only for reversible/governed memory writes under explicit eligibility test.

### P-2 (P2) Inconsistent modal verbs
**Observation**
- Mix of MUST/Always/Prefer/Normally can reduce predictability.

**Recommendation**
- Adopt modal taxonomy:
  - MUST = invariant
  - SHOULD = preferred unless documented reason
  - MAY = optional
- Run a wording normalization pass.

---

## 4) Cognitive Load Assessment

### L-1 (P1) High nested-condition complexity in stage specs
**Where**
- `auto-bean-process`, `auto-bean-categorize`, and import stage references.

**Impact**
- Increased execution error probability and missed clauses under long-context operation.

**Recommendation**
- Introduce per-stage “Fast Path Checklist” at top (8-12 bullets max), with deep details below.

### L-2 (P2) Repetition across shared and stage files
**Impact**
- Duplicated policy increases drift risk.

**Recommendation**
- Move repeated constraints (question broker rule, memory boundaries, status payload boundaries) into a single canonical section and refer by anchor.

### L-3 (P2) Reference loading choreography is strict but mentally expensive
**Observation**
- Import skill demands sequential opening of references, then supplemental triggers.

**Recommendation**
- Add “reference dependency map” table: stage -> required refs -> optional refs -> done criteria.

---

## 5) Semantic Coverage (Intent/Failure-path Gaps)

### S-1 (P1) Missing explicit timeout/retry policy for external command stages
**Where**
- `auto-bean-process` uses docling, but lacks explicit timeout, max retries, and fallback cadence.

**Recommendation**
- Define command timeout, retry count, and deterministic error classification.

### S-2 (P1) Partial coverage for malformed artifact recovery
**Where**
- Contracts discuss missing paths, but less explicit on malformed markdown/json sections in existing artifacts.

**Recommendation**
- Add repair protocol: preserve original + append `Recovery Notes` + continue/stop criteria.

### S-3 (P2) Insufficient explicit handling for status/artifact divergence resolution
**Where**
- Mentioned in places, but no single tie-break rule hierarchy.

**Recommendation**
- Define precedence order (e.g., source file existence > status pointer > artifact references), plus reconciliation steps.

### S-4 (P2) Query skill could define escalation path for non-BQL analytical needs
**Recommendation**
- Add explicit branch for when BQL cannot answer safely (e.g., derived valuation), with handoff guidance.

---

## 6) Composition Conflict Analysis (Markdown link/import interplay)

### X-1 (P1) Imported strict rules are sometimes softened in downstream skill wording
**Examples**
- Shared question contract is absolute; stage text sometimes says “normally.”

**Fix**
- Ensure downstream files never weaken imported constraints.

### X-2 (P2) Ownership map vs stage-specific end-of-session rules
**Examples**
- Ownership map broad claim on memory writes conflicts with stage-specific `MEMORY.md` update instructions.

**Fix**
- Split ownership table row into “workflow JSON memory” and “global MEMORY.md”.

### X-3 (P2) Artifact-contract boundaries and stage summaries can still duplicate detail
**Examples**
- Some stage returns request rich detail that contract discourages duplicating in import artifact.

**Fix**
- Add examples of “allowed summary” vs “forbidden copied payload.”

---

## Prioritized Improvement Plan

## P0 (Immediate)
1. Resolve memory write ownership contradiction (`MEMORY.md` vs memory-only writer claim).
2. Normalize import-invoked sub-agent wording to absolute no-direct-user-question rule.

## P1 (Next sprint)
3. Add shared operational definition of “fail closed.”
4. Add fast-path checklists to process/categorize/import stages.
5. Standardize deterministic triggers for “read when needed.”
6. Require always-on (possibly short-form) categorize artifact for audit continuity.
7. Add timeout/retry/error taxonomy for docling processing.

## P2 (Backlog)
8. Normalize modal verbs (MUST/SHOULD/MAY) across all skill docs.
9. Reduce repeated policy text by centralizing and linking anchors.
10. Add malformed artifact repair protocol.
11. Add status/artifact divergence precedence and reconciliation recipe.
12. Expand query skill non-BQL escalation guidance.
13. Add explicit examples to reduce artifact detail duplication drift.

---

## Suggested Implementation Sequence

1. Patch shared docs first (`workflow-rules.md`, `ownership-map.md`, `question-handling-contract.md`).
2. Then patch stage SKILL files to align with tightened shared language.
3. Finally update import reference docs to enforce summary/detail boundaries with concrete examples.

This order minimizes churn and prevents repeated edits across stage-specific files.
