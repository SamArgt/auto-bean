---
name: auto-bean-apply
description: Review and finalize structural ledger or workspace changes through a skill-first Codex workflow. Use when you need to turn reviewed normalized statement evidence into candidate Beancount postings or make another direct structural workspace edit.
---

Follow this workflow:

1. Restate the requested structural change in plain language.
2. If the request is import-derived transaction posting, inspect the reviewed `statements/parsed/*.json` inputs, current ledger files, and any bounded `.auto-bean/memory/import_sources/` hints before drafting changes.
3. Inspect the affected workspace files and summarize:
   - what changed
   - why it changed
   - which files are affected
4. Read `.agents/skills/shared/beancount-syntax-and-best-practices.md` before drafting Beancount transactions or other ledger directives.
5. When drafting Beancount transactions, consult Beancount documentation through Context7 before encoding authoritative assumptions about transaction syntax, balancing behavior, or `open` directive currency constraints.
   - Use the standard transaction shape: dated transaction header plus postings.
   - Prefer explicit, inspectable postings even though Beancount can infer one missing balancing amount.
   - Respect currency constraints declared on `open` directives, or fail closed during validation.
6. Apply the scoped structural mutation directly in the working tree.
7. If the mutation writes Beancount transactions derived from reviewed import evidence, update the relevant `statements/import-status.yml` entries after those transactions are written in the workspace.
   - set `status: in_review` for the specific statement entries once those transactions are written
   - keep `status: parsed` or `status: parsed_with_warnings` only until posting work has not started yet
   - refresh the status metadata in the same file instead of creating a second workflow-tracking file
   - do not set `status: done` before validation succeeds and commit/push approval is obtained
8. Run post-mutation validation before any finalization claim. For ledger changes, prefer `./scripts/validate-ledger.sh` or `./.venv/bin/bean-check ledger.beancount`.
9. Present a concise post-mutation review package before any commit or push step:
   - a short summary of what changed and why
   - the affected files
   - parsed statement facts when the change came from import evidence
   - the `statements/import-status.yml` update when import-derived transactions were written
   - reused source-context hints when they influenced posting generation
   - derived ledger edits
   - validation outcome
   - a `git diff -- <paths>` view, or the most relevant equivalent diff output for the changed files
10. Ask for explicit approval before commit or push finalization. If approval is denied, deferred, or cannot be obtained, leave the mutation in the working tree and describe it as unfinalized.
11. After validation succeeds and the workflow is explicitly finalized, update the same `statements/import-status.yml` entries to `status: done`.
12. Suggest source-context create or update only after a trustworthy finalized outcome; let the orchestrator decide whether to write it

Guardrails:

- Keep the scope limited to structural ledger and workspace changes, including candidate transaction postings derived from reviewed import evidence.
- Treat commit/push approval as a hard trust boundary.
- Do not silently finalize `ledger.beancount` or `beancount/**` changes.
- Do not leave `statements/import-status.yml` stale when import-derived transactions were actually written.
- Do not skip the `in_review` state when transactions have been written but validation/finalization is still pending.
- Do not treat `.auto-bean/memory/import_sources/` guidance as authority to skip current-evidence checks, validation, or approval.
- Use Python/package helpers only when they support this authored workflow instead of replacing it.
- Preserve high scrutiny for canonical `ledger.beancount` and `beancount/**` changes even when direct mutation is the normal path.
- Never imply that a working-tree mutation has been accepted into history before explicit approval and successful finalization.
