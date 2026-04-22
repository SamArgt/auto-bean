---
name: auto-bean-apply
description: Review and finalize structural ledger or workspace changes through a skill-first Coding agent workflow. Use when you need to turn reviewed normalized statement evidence into candidate Beancount postings or make another direct structural workspace edit.
---

Read these references before acting:

- `.agents/skills/shared/beancount-syntax-and-best-practices.md`
- `.agents/skills/auto-bean-apply/references/reconciliation-findings.md` when import-derived postings need transfer, duplicate, or balancing review
- `.agents/skills/auto-bean-apply/references/clarification-guidance.md` when import-derived postings remain ambiguous, unfamiliar, or blocked on user clarification

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
6. Draft the scoped structural mutation directly in the working tree.
   - For import-derived posting work, write the candidate Beancount transactions into the workspace before presenting the review package.
   - Keep the drafted transactions explicit and inspectable so findings and follow-up decisions can refer to concrete candidate entries.
   - Describe this state as the resulting working-tree mutation, not as a proposal artifact or an accepted history change.
7. If the mutation writes Beancount transactions derived from reviewed import evidence, run reconciliation checks on the drafted workspace result before any finalization claim.
   - Compare drafted candidate postings against the current ledger, same-run candidate postings, and the reviewed parsed evidence.
   - Surface findings under these distinct buckets only:
     - `likely_transfer`
     - `possible_duplicate`
     - `unbalanced`
     - `currency_risk`
     - `possible_future_transfer`
   - Use `possible_future_transfer` when a transfer pattern looks strong but no existing or same-run counterpart ledger booking matches yet.
   - Keep findings evidence-driven and deterministic. Anchor them in parsed statement facts, drafted candidate posting details, existing ledger entries, declared account constraints, links, or imported ids when present.
   - Fail closed when the workflow cannot safely classify or resolve a finding. Do not guess, auto-net, auto-merge, or silently rewrite the candidate postings.
8. If the mutation writes Beancount transactions derived from reviewed import evidence and the drafted result still depends on an ambiguous or unfamiliar interpretation, stop at a clarification checkpoint before any finalization claim.
   - Read `.agents/skills/auto-bean-apply/references/clarification-guidance.md` before asking the user anything.
   - Explain uncertainty from concrete evidence in `statements/parsed/*.json`, current ledger context, declared account constraints, reused source-context hints when relevant, and the drafted candidate postings.
   - Ask only the minimum bounded questions needed to unblock the risky interpretation. Prioritize account choice, transfer intent, duplicate suspicion, or source-specific meaning over open-ended interrogation.
   - Distinguish confirmed facts from inferences. Say what was observed, what interpretations remain plausible, what could go wrong if the workflow guesses, and what user answer would let it proceed safely.
   - Do not ask for commit, push, or final finding decisions while clarification is still unresolved.
9. When the user answers a clarification request, resume from the same clarification record before any finalization claim.
   - Update the drafted changes in the working tree to reflect the user's answer.
   - Show how the answer changed account mapping, transfer or duplicate handling, warning status, blocker status, or candidate postings before commit or push approval.
   - Re-run reconciliation checks and validation if the answer changed drafted postings, findings, or supporting directives.
   - If the user response is still ambiguous, contradictory, or insufficient, fail closed: ask one more bounded clarification question or leave the result blocked rather than forcing an interpretation.
   - If the clarified outcome reveals a narrow, reusable source-specific pattern, suggest a targeted update to the source-context memory file after the current result is trustworthy and reviewable.
   - Keep any suggested memory update attributable to current evidence and current user input; do not silently promote it into broad preference memory here and do not write the memory file without approval.
10. If the mutation writes Beancount transactions derived from reviewed import evidence, update the relevant `statements/import-status.yml` entries after those transactions are written in the workspace.
   - set `status: in_review` for the specific statement entries once those transactions are written
   - keep `status: parsed` or `status: parsed_with_warnings` only until posting work has not started yet
   - refresh the status metadata in the same file instead of creating a second workflow-tracking file
   - do not set `status: done` before validation succeeds and commit/push approval is obtained
11. Run post-mutation validation before any finalization claim. For ledger changes, prefer `./scripts/validate-ledger.sh` or `./.venv/bin/bean-check ledger.beancount`.
12. Present a concise post-mutation review package before any commit or push step:
   - a short summary of what changed and why
   - the affected files
   - parsed statement facts when the change came from import evidence
   - the `statements/import-status.yml` update when import-derived transactions were written
   - reused source-context hints when they influenced posting generation
   - drafted ledger edits
   - reconciliation findings and a concrete suggested action for each finding
   - a short explanation of the clarification asked and how the user answer changed the result when a clarification checkpoint was required
   - validation outcome, with confirmed validation failures called out separately from inferred risks or follow-up concerns
   - a `git diff -- <paths>` view, or the most relevant equivalent diff output for the changed files
   - a clear statement that the working tree is mutated but still unfinalized until commit or push approval is granted
13. Ask the user for a decision on each reconciliation finding before finalization.
   - Present each finding as a separate decision item tied to the drafted postings it affects.
   - Include the suggested action for that finding, but do not apply it until the user chooses.
   - If there are no findings, say so explicitly and continue with the normal finalization decision.
14. Apply the user-selected action for each finding in the working tree.
   - Re-run reconciliation checks and validation if the chosen actions change the drafted transactions or supporting directives.
   - Keep unresolved findings visible if the user chooses to defer, keep-as-is, or otherwise leave them unresolved.
15. Ask for explicit approval before commit or push finalization only after the finding decisions have been applied and the current workspace result has been revalidated. If approval is denied, deferred, or cannot be obtained, leave the mutation in the working tree and describe it as unfinalized.
16. After validation succeeds and the workflow is explicitly finalized, update the same `statements/import-status.yml` entries to `status: done`.
17. Suggest source-context create or update only after a trustworthy finalized outcome, including reusable clarification outcomes when they clearly fit the source-specific memory boundary; let the orchestrator decide whether to write it.
18. When the user asks how to undo a committed mutation, explain the git-backed recovery path from the recorded commit history.
   - Prefer reverting the recorded commit over silently overwriting ledger files.

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
- Do not silently drop, merge, or rewrite candidate postings just because a transfer or duplicate pattern looks plausible.
- Do not apply a suggested action for a finding until the user has made a decision on that finding.
- Do not bypass the clarification checkpoint with a best guess when account identity, transfer intent, duplicate suspicion, source-specific meaning, or balancing rationale is still materially ambiguous.
- Do not describe rollback as ad hoc file replacement when the mutation has already been committed; prefer `git revert` or the equivalent revert-based history-preserving path.
