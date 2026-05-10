# Skills Prompt Evaluation Report

Date: 2026-05-06
Reviewer: Codex
Scope: `skill_sources/**/*.md`, `skill_sources/**/agents/openai.yaml`, and `workspace_template/AGENTS.md`.

Note: the requested `workspace/AGENTS.md` path does not exist in this product repo. I evaluated `workspace_template/AGENTS.md` because it is the authored workspace agent template that becomes the user-workspace `AGENTS.md`.

## Executive Summary

The skill set is coherent and conservative overall. The strongest design choices are narrow worker ownership, explicit ledger mutation boundaries, status/artifact separation, and shared question-handling rules. Most risks are not severe contradictions; they are second-order prompt quality issues that can cause inconsistent execution when many linked instructions are loaded together.

Top risks:

1. `auto-bean-memory` is intended to take initiative on durable memory writes, but the approval/visibility language should be rewritten so autonomous persistence is clearly allowed and every update is surfaced afterward.
2. `ready` status means both "eligible for processing" and "blocked/manual retry hold," which is handled by metadata but still semantically overloaded.
3. Import uses sub-agents heavily, but runtime system policy may not always permit sub-agent spawning; no fallback path is specified.
4. Several worker prompts require large multi-field return bundles without a compact schema, increasing execution variance.
5. Linked references mostly reinforce each other, but there are a few composition drifts around who waits for user input and when memory may be persisted.

## 1. Contradiction Detection

### CD-1: Memory initiative policy needs clearer post-write visibility

Evidence:

- `skill_sources/auto-bean-memory/SKILL.md:3` describes memory as persisting "approved reusable decisions."
- `skill_sources/auto-bean-memory/SKILL.md:37` says to persist reusable decisions from workflow evidence "even without an explicit user request."
- `skill_sources/shared/memory-access-rules.md:78` says "Persist only approved reusable decisions."
- `skill_sources/auto-bean-categorize/references/clarification-guidance.md:38` says "Do not persist memory automatically."

Impact: the intended product behavior is agent initiative: `$auto-bean-memory` should be allowed to persist narrow, evidence-backed reusable learning without prior user approval. The prompt risk is that "approved" and "do not persist memory automatically" can suppress that initiative or make agents ask before every memory write. The boundary should instead require conservative eligibility checks plus immediate surfacing of what changed.

Suggested rewrite:

```md
Take initiative to persist reusable decisions when workflow evidence makes them narrow, current, and safe to reuse. Prior user approval is not required for eligible memory writes.

Do not persist broad preferences, tentative guesses, unresolved clarifications, rejected interpretations, validation-failed outcomes, or records that would bypass current evidence checks. After every durable memory change, surface what was written, why it was eligible, the source/audit context, the exact path changed, and limits on future reuse.
```

### CD-2: `ready` status is both retryable and manually blocked

Evidence:

- `skill_sources/auto-bean-import/SKILL.md:29-32` treats `ready` as process-eligible only below the retry/manual-hold threshold.
- `skill_sources/auto-bean-process/SKILL.md:64` sets `ready` when no trustworthy parsed evidence exists or manual follow-up is required.
- `workspace_template/AGENTS.md:56` defines `ready` owner next action as import may assign process, but blocked by "missing parser-ready evidence or manual retry hold."

Impact: the metadata resolves the loop risk, but the status name still carries opposing meanings: "ready to process" and "not ready until manual resolution." Agents scanning only status names can make poor scheduling decisions.

Suggested rewrite: keep `ready` for processable work and introduce `manual_resolution` or `process_blocked`, or update every status table and discovery rule to say "`ready` is a queue state, not a guarantee of processability; check `manual_resolution_required` before dispatch."

### CD-3: Direct-use question handling can conflict with import-brokered ownership

Evidence:

- `skill_sources/shared/workflow-rules.md:38-42` says import-invoked workers return questions to `$auto-bean-import`, while direct-use skills may ask the user themselves.
- `skill_sources/auto-bean-categorize/references/clarification-guidance.md:18` says "Wait for the user answer before continuing unresolved decisions."
- `skill_sources/auto-bean-categorize/SKILL.md:77` says import-invoked categorize normally returns question ids so import can keep the main thread.

Impact: the intended behavior is recoverable from context, but the linked clarification reference reads like the worker itself waits, which can fight the import-broker rule in a loaded context.

Suggested rewrite in `clarification-guidance.md`:

```md
If direct-use, wait for the user answer before continuing unresolved decisions.
If import-invoked, return the question metadata to `$auto-bean-import`; continue only after `$auto-bean-import` resumes this artifact with the answer.
```

### CD-4: Sub-agent requirement conflicts with environments where delegation is unavailable

Evidence:

- `skill_sources/auto-bean-import/SKILL.md:35-39`, `74-79`, `98-103`, and `110-113` require sub-agent delegation.
- The broader runtime may restrict sub-agent creation unless explicitly permitted by current system context.

Impact: import becomes impossible in environments where sub-agent spawning is unavailable, despite the workflow being otherwise executable serially.

Suggested rewrite:

```md
Prefer one sub-agent per statement when the current runtime permits delegation. If sub-agents are unavailable, process statements serially while preserving the same stage boundaries, artifacts, and return contracts.
```

## 2. Semantic Ambiguity

### SA-1: "Approved" obscures the intended autonomous memory model

Problem: "approved reusable decisions" may imply prior user approval, which conflicts with the desired behavior that `$auto-bean-memory` should take initiative when evidence is narrow and safe.

Rewrite: replace "approved reusable decisions" with "eligible reusable decisions" and define eligibility in terms of current evidence, source/audit provenance, narrow scope, non-tentative outcome, and required post-write summary.

### SA-2: "Strong evidence" and "confident match" lack thresholds

Evidence:

- `skill_sources/auto-bean-import/SKILL.md:58` allows account inference when evidence is "strong."
- `skill_sources/auto-bean-categorize/SKILL.md:50` uses "confident match."
- `skill_sources/shared/memory-access-rules.md:70` says to skip memory that is stale or broad.

Impact: agents may vary widely on when to act versus ask.

Rewrite:

```md
Treat evidence as strong only when at least two independent current facts agree, such as institution/account identity plus currency, or external id plus amount/date. Memory alone never makes evidence strong.
```

### SA-3: "When useful" weakens artifact creation expectations

Evidence:

- `skill_sources/auto-bean-categorize/SKILL.md:65-70` says create or update a categorize artifact "when useful," but the same skill expects pending questions, warnings, blockers, and memory suggestions to live there.

Impact: a worker may skip artifact creation for a simple categorization, then later have nowhere canonical to record a late blocker or memory suggestion.

Rewrite:

```md
Create a categorize artifact whenever there are reconciliation findings, pending or answered questions, blockers, warnings, memory suggestions, or posting inputs too large for a compact return. For trivial no-blocker work, returning without an artifact is allowed.
```

### SA-4: "Intermediate import artifact" is not defined

Evidence:

- `skill_sources/auto-bean-categorize/SKILL.md:3` and `:10` mention an "intermediate import artifact."

Impact: this can be confused with parsed evidence, import-owned artifact, or a temporary handoff document.

Rewrite: name the accepted artifact type explicitly, for example "one parsed statement JSON file, or one explicit import-provided Markdown handoff artifact that points to a parsed statement and status entry."

### SA-5: "Structural mutation workflow" is not named

Evidence:

- `skill_sources/auto-bean-query/SKILL.md:51` says to hand off to "the structural mutation workflow."

Impact: there is no named skill for generic structural edits, while import owns first-seen account directives and write owns transaction entries plus minimum supporting directives.

Rewrite: "If the user wants a transaction entry or minimal transaction-supporting directive, hand off to `$auto-bean-write`; if the request is account structure for an import, hand off to `$auto-bean-import`; otherwise ask for the intended mutation workflow."

## 3. Persona Consistency

### Current persona profile

The authored skill persona is consistent: cautious, audit-oriented, fail-closed, evidence-first, and user-approval-sensitive. `workspace_template/AGENTS.md` reinforces this with "Codex is the orchestrator" and installed skills as the execution surface.

### Tone drift risks

1. Worker prompts are mostly operational and terse, while artifact guidance asks for "user-friendly" and "non-technical" fillable artifacts. That is a productive tension, not a contradiction, but it would benefit from a shared style line: "Artifact language should be plain and reviewable; internal returns may be compact and technical."
2. `auto-bean-memory` is deliberately more initiative-forward than the rest of the suite. That is acceptable, but the persona should be "proactive and accountable": write eligible memory without prior approval, then plainly surface the update and reuse limits.
3. The prompts sometimes address Codex as orchestrator, worker, reviewer, and mutation author in the same workflow. The roles are clearly scoped by skill, but `auto-bean-import` has the most persona load because it is both broker and account-structure mutator.

Suggested persona anchor:

```md
Across all auto-bean skills: be conservative with financial facts, explicit about uncertainty, and proactive only when the action is reversible, workflow-eligible, or already approved by workflow state. Durable memory requires clear eligibility provenance and post-write disclosure; ledger history requires explicit user approval before finalization.
```

## 4. Cognitive Load Assessment

### High-load files

| File | Approx. lines | Load risk | Notes |
| --- | ---: | --- | --- |
| `skill_sources/auto-bean-import/SKILL.md` | 136 | High | 11 workflow phases, multiple sub-agent stages, status transitions, artifacts, first-seen accounts, cross-statement review, writing, memory handoff. |
| `skill_sources/auto-bean-categorize/SKILL.md` | 109 | Medium-high | Single-statement scope helps, but return contract and artifact rules are dense. |
| `skill_sources/auto-bean-write/SKILL.md` | 97 | Medium | Clear linear flow, but direct-use vs import-invoked behavior adds branching. |
| `skill_sources/auto-bean-memory/SKILL.md` | 79 | Medium | Compact, but memory category mapping and approval rules carry high consequence. |
| `workspace_template/AGENTS.md` | 100 | Medium | Good overview, but status table plus deep policy duplicates linked skill rules. |

### Load hotspots

- `auto-bean-import` has deeply nested conditions around `ready`, process attempts, current fingerprints, manual resolution, and explicit reprocess requests.
- `auto-bean-import` phases 7-8 require reading multiple categorize artifacts, updating cross-statement notes, batching user questions, and preserving ownership boundaries.
- `auto-bean-categorize` asks for categorization, reconciliation, deduplication, memory suggestions, pending questions, artifact updates, status updates, and posting inputs in one worker pass.
- `auto-bean-write` step 12 is a long compound rule that combines direct approval, import-invoked return shape, deferred approval, and current working-tree state.

### Recommendations

1. Add compact return schemas to worker skills:

```yaml
assigned_path:
status_update:
artifacts:
blockers:
pending_questions:
safe_work_completed:
memory_suggestions:
validation:
```

2. Split `auto-bean-import` into a shorter orchestration body plus linked phase references if it continues to grow.
3. Replace repeated "do not copy full warning/question/answer payloads" bullets with one shared artifact-boundary reference that each skill cites.
4. Put status transition rules into one table shared by import, process, categorize, and workspace `AGENTS.md`.

## 5. Semantic Coverage

### Covered well

- Raw statement discovery, processing, categorization, posting, final review, and memory handoff are covered.
- Read-only query boundaries are strong.
- Ledger mutation validation and final approval boundaries are explicit.
- Status/artifact separation is covered in both skills and shared references.
- Memory file shape and allowed categories are covered.
- User question persistence and resumption are covered.

### Coverage gaps

1. Missing installed-skill reference failure path
   - Skills say "Always read" runtime paths under `.agents/skills/...`, but do not say what to do if an installed reference is missing. Add: "If a required installed reference is missing, report the missing path and stop that stage rather than guessing."

2. Missing serial fallback for import
   - Covered above in CD-4.

3. Missing malformed status recovery
   - `import-status-reading.md` says use YAML parser and keep the file small, but does not specify recovery behavior for malformed YAML, duplicate keys, unknown statuses, or path conflicts beyond general fail-closed language.

4. Missing partial-write recovery path
   - `auto-bean-write` validates after drafting but does not say whether to revert, amend, or leave failed draft edits when validation fails. The repo-level policy says avoid destructive resets, so the skill should say: "Leave failed draft edits in place unless user asks to revert; summarize changed files and validation failure."

5. Missing direct account-structure workflow outside import
   - Import handles first-seen accounts; write handles transaction entries and minimum supporting directives. There is no clear owner for user requests like "open a new brokerage account in my ledger" outside statement import.

6. Missing max parallelism guidance
   - Import says one sub-agent per statement. Large batches could create too much concurrent work. Add a bounded default, such as "batch parallel workers in groups of 3-5 unless the runtime or user says otherwise."

7. Missing secret/privacy handling for artifacts
   - Skills avoid raw statement dumps and full ledger excerpts, but there is no single privacy rule for account numbers, tokens, tax IDs, or full card numbers in Markdown artifacts.

8. Missing external dependency fallback for `docling`
   - Process mandates `./.venv/bin/docling`; no clear path if the workspace installed it elsewhere or only `uv run docling` works.

## 6. Composition Conflict Analysis

This section checks prompt files against the references they import through Markdown-style path links.

### CCA-1: `auto-bean-memory` vs `memory-access-rules.md`

Conflict: `auto-bean-memory` correctly encourages autonomous persistence from workflow evidence, while `memory-access-rules.md` can be read as requiring prior approval because it says to persist only approved reusable decisions.

Severity: Medium-high.

Fix: replace approval-gated wording with eligibility-gated wording, and require post-write disclosure for every durable memory update.

### CCA-2: `auto-bean-categorize` vs `clarification-guidance.md`

Conflict: the main skill says import-invoked categorize should return question ids and artifact paths; clarification guidance says to wait for the user answer. The guidance later mentions `$auto-bean-import` supplying the answer, but the "wait" instruction is not scoped.

Severity: Medium.

Fix: split direct-use and import-invoked behavior in the reference.

### CCA-3: `auto-bean-import` vs `import-artifact-contract.md`

Potential conflict: the import skill tells the orchestrator to update import-owned artifacts with many summaries and decisions. The contract correctly says not to include operational counts/current status/retry counters and not to copy worker-owned payloads. The skill mostly honors this, but phrases like "consolidate all artifacts, questions, answers, decisions, and validation results" in `auto-bean-import/SKILL.md:106` can be overread as copying detail.

Severity: Medium-low.

Fix: change "consolidate all artifacts, questions, answers..." to "consolidate links, ids, summaries, decisions, and validation outcomes..."

### CCA-4: `workspace_template/AGENTS.md` vs skill-specific ownership

No major conflict. The workspace template accurately summarizes import as final approval and commit/push broker, query as read-only, write as transaction writing, and memory as the only memory writer.

Small drift: `workspace_template/AGENTS.md:34` says "When any skill needs user input," follow the shared question-handling rules. Direct-use memory inspection/correction may need ordinary clarification that is not tied to statement artifacts. This is minor because the rules include direct-use skills, but the phrase could be "When workflow work needs user input..."

### CCA-5: Runtime paths in authored sources

Potential conflict: source files in `skill_sources/` link to installed runtime paths under `.agents/skills/...`. This is architecturally intentional, but repo-only reviewers may misinterpret them as broken local links.

Severity: Low.

Fix: add a short comment in contributor docs or the report index: "Authored skills use installed workspace paths because `auto-bean init` materializes `skill_sources/` into `.agents/skills/`."

## Prioritized Remediation Plan

1. Define autonomous memory eligibility and post-write disclosure, then align `auto-bean-memory`, `memory-access-rules.md`, and `clarification-guidance.md`.
2. Rename or clarify `ready` status so manual retry hold cannot be mistaken for processable work.
3. Add serial fallback and max parallelism guidance to `auto-bean-import`.
4. Scope clarification guidance's "wait for user answer" rule by direct-use vs import-invoked mode.
5. Add compact worker return schemas for process, categorize, write, and memory.
6. Add missing failure paths for absent installed references, malformed status YAML, failed validation after draft edits, and unavailable `docling`.
7. Add one privacy rule for artifacts that forbids full account numbers, secret tokens, tax IDs, and raw statement dumps unless explicitly required and approved.

## Suggested Rewrite Snippets

### Autonomous memory persistence

```md
Durable memory writes do not require prior user approval when `$auto-bean-memory` can verify that the reusable decision is narrow, evidence-backed, current, and safe to reuse. Worker memory suggestions are candidates, not commands; validate them before writing. After every durable change, surface the exact memory path changed, the decision persisted, why it was eligible, source/audit context, and future reuse limits.
```

### Import parallelism fallback

```md
Prefer parallel sub-agents for independent statements when the runtime permits it. For large batches, use small groups of 3-5 statements unless the user requests otherwise. If delegation is unavailable, run the same stages serially and preserve all artifact, status, and handoff contracts.
```

### Clarification broker

```md
For direct-use work, ask the bounded question and wait. For import-invoked work, persist the question in the stage-owned artifact and return the question id, artifact path, and blocker flag to `$auto-bean-import`; continue only when `$auto-bean-import` resumes the artifact with the answer.
```

### Failed validation after ledger draft

```md
If validation fails after a draft edit, do not claim success or finalize. Leave the working-tree edit in place unless the user explicitly asks to revert it, report the changed files, validation command, concrete failure, and the smallest proposed fix.
```

## Final Assessment

The prompts are strong enough to drive the intended product workflow, especially after the prior addition of import-owned artifacts and retry metadata. The highest-value next pass is not adding more rules; it is reducing interpretation variance by naming approval states, separating direct-use from import-invoked branches, and moving repeated return expectations into compact schemas.
