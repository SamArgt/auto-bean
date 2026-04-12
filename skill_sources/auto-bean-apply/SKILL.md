---
name: auto-bean-apply
description: Review and finalize structural ledger or workspace changes through a skill-first Codex workflow. Use when Codex needs to make a direct structural workspace edit, validate the result, summarize the change, show `git diff` before commit or push, capture optional governed proposal artifacts for deeper review, ask for explicit approval at the commit/push boundary, and preserve audit artifacts under `.auto-bean/`.
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
3. Apply the scoped structural mutation directly in the working tree when it is within the skill's authority. Distinguish clearly between "the working tree changed" and "the change was accepted into history."
4. Run post-mutation validation before any finalization claim. For ledger changes, prefer `./scripts/validate-ledger.sh` or `./.venv/bin/bean-check ledger.beancount`.
5. Present a concise post-mutation review package before any commit or push step:
   - a short summary of what changed and why
   - the affected files
   - validation status
   - a `git diff -- <paths>` view, or the most relevant equivalent diff output for the changed files
6. If the user asks for deeper inspection, or the change is unusually risky, create a governed proposal artifact under `.auto-bean/proposals/` as supplemental review context. Proposal artifacts are optional review aids, not the default safety model.
7. Ask for explicit approval before commit or push finalization. If approval is denied, deferred, or cannot be obtained, leave the mutation in the working tree and describe it as unfinalized.

Guardrails:

- Keep the scope limited to structural ledger and workspace changes.
- Treat commit/push approval as a hard trust boundary.
- Do not silently finalize `ledger.beancount` or `beancount/**` changes.
- Use Python/package helpers only when they support this authored workflow instead of replacing it.
- Preserve high scrutiny for canonical `ledger.beancount` and `beancount/**` changes even when direct mutation is the normal path.
- Never imply that a working-tree mutation has been accepted into history before explicit approval and successful finalization.
