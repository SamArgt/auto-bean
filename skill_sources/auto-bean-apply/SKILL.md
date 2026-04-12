---
name: auto-bean-apply
description: Review and finalize structural ledger or workspace changes through a skill-first Codex workflow. Use when Codex needs to turn reviewed normalized statement evidence into candidate Beancount postings or make another direct structural workspace edit, validate the result, summarize the change, show `git diff` before commit or push, capture optional governed proposal artifacts for deeper review, ask for explicit approval at the commit/push boundary, and preserve audit artifacts under `.auto-bean/`.
---

Load `.agents/skills/shared/mutation-pipeline.md` and `.agents/skills/shared/mutation-authority-matrix.md` before acting.
When the request involves posting transactions from reviewed import evidence, also load `.agents/skills/auto-bean-apply/references/posting-plan.example.json` before mutating the ledger.

Follow this workflow:

1. Restate the requested structural change in plain language.
2. If the request is import-derived transaction posting, inspect the reviewed `statements/parsed/*.json` inputs, current ledger files, and any bounded `.auto-bean/memory/import_sources/` hints before drafting changes.
3. Build or update a versioned posting-plan artifact when transaction postings are involved:
   - keep all contract keys in `snake_case`
   - keep parsed statement facts separate from derived ledger edits
   - record which prior source-context hints were reused, which current evidence still drove the outcome, and which hints were ignored
   - keep reused guidance advisory and reviewable
   - keep candidate postings separate from accepted git history until validation succeeds and the user approves finalization
4. Inspect the affected workspace files and summarize:
   - what changed
   - why it changed
   - which files are affected
   - whether the change is routine or materially meaningful
   - why it looks safe or risky in ledger context
5. When drafting Beancount transactions, consult Beancount documentation through Context7 before encoding authoritative assumptions about transaction syntax, balancing behavior, or `open` directive currency constraints.
   - Use the standard transaction shape: dated transaction header plus postings.
   - Prefer explicit, inspectable postings even though Beancount can infer one missing balancing amount.
   - Respect currency constraints declared on `open` directives, or fail closed during validation.
6. Apply the scoped structural mutation directly in the working tree when it is within the skill's authority. Distinguish clearly between "the working tree changed" and "the change was accepted into history."
7. Run post-mutation validation before any finalization claim. For ledger changes, prefer `./scripts/validate-ledger.sh` or `./.venv/bin/bean-check ledger.beancount`.
8. Present a concise post-mutation review package before any commit or push step:
   - a short summary of what changed and why
   - the affected files
   - parsed statement facts when the change came from import evidence
   - reused source-context hints when they influenced posting generation
   - derived ledger edits
   - validation outcome
   - a `git diff -- <paths>` view, or the most relevant equivalent diff output for the changed files
9. If the user asks for deeper inspection, or the change is unusually risky, create a governed proposal artifact under `.auto-bean/proposals/` as supplemental review context. Proposal artifacts are optional review aids, not the default safety model.
10. Ask for explicit approval before commit or push finalization. If approval is denied, deferred, or cannot be obtained, leave the mutation in the working tree and describe it as unfinalized.
11. If validation fails, mappings remain low confidence, or the transaction outcome is otherwise blocked, keep the candidate postings unfinalized and record narrow audit context under `.auto-bean/artifacts/`.

Guardrails:

- Keep the scope limited to structural ledger and workspace changes, including candidate transaction postings derived from reviewed import evidence.
- Treat commit/push approval as a hard trust boundary.
- Do not silently finalize `ledger.beancount` or `beancount/**` changes.
- Do not treat `.auto-bean/memory/import_sources/` guidance as authority to skip current-evidence checks, validation, or approval.
- Use Python/package helpers only when they support this authored workflow instead of replacing it.
- Preserve high scrutiny for canonical `ledger.beancount` and `beancount/**` changes even when direct mutation is the normal path.
- Never imply that a working-tree mutation has been accepted into history before explicit approval and successful finalization.
