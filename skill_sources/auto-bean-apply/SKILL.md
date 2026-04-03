---
name: auto-bean-apply
description: Review and apply structural ledger or workspace changes through a skill-first Codex workflow. Use when Codex needs to summarize a proposed structural change, distinguish routine edits from materially meaningful ledger changes, create optional governed proposal artifacts, ask for explicit validation and approval, and preserve review artifacts under `.auto-bean/`.
---

Load `.agents/skills/shared/mutation-pipeline.md` and `.agents/skills/shared/mutation-authority-matrix.md` before acting.

Follow this workflow:

1. Restate the requested structural change in plain language.
2. Inspect the affected workspace files and summarize:
   - what changed
   - why it changed
   - which files are affected
   - whether the change is routine or materially meaningful
   - why it looks safe or risky in ledger context
3. If the user requests deeper inspection, or the change is risky enough to justify it, create a governed proposal artifact under `.auto-bean/proposals/`.
4. Ask the user to validate the proposed change explicitly.
5. Do not commit, apply, or describe the change as accepted until explicit approval and post-change validation both succeed.
6. Preserve governed review artifacts under `.auto-bean/artifacts/`.

Guardrails:

- Keep the scope limited to structural ledger and workspace changes.
- Treat approval as a hard trust boundary.
- Do not silently mutate `ledger.beancount` or `beancount/**`.
- Use Python/package helpers only when they support this authored workflow instead of replacing it.
