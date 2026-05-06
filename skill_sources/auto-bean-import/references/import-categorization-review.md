# Import Categorization Review

Use for categorization sub-agent handoff, cross-statement review, and user review before writing.

## 1. Categorization Handoff

- For each statement at `categorize_ready`, spawn a sub-agent for that parsed statement and instruct it to use `$auto-bean-categorize`.
- Require the categorize return schema.
- Keep statements with clarification, repair, or manual source blockers at `categorize_blocked` and out of posting and final approval.
- After user answers for `categorize_blocked`, resume `$auto-bean-categorize`; it must return `categorize_review` before the statement can advance to writing.
- Gate: continue to cross-statement review only after every categorize sub-agent has returned `categorize_review` or `categorize_blocked`.

## 2. Cross-Statement Review

- Before surfacing categorize findings, read categorize artifacts and posting inputs for statements in the same batch that reached `categorize_review`.
- Compare candidates for likely transfers, duplicates, mirror-image amounts, nearby dates, matching currencies, complementary descriptions, shared references, fees, FX legs, and account-pair patterns.
- Use `$auto-bean-query` for existing ledger activity when needed.
- Record only reviewable candidates; do not auto-drop, auto-net, or silently mark duplicates without strong current evidence or approved user input.
- When a likely transfer or duplicate spans artifacts, update each categorize artifact with a labeled `Import Batch Cross-Statement Review` section and update import-owned artifacts with links, ids, summaries, and posting impact.
- Gate: continue to user review only with statements still at `categorize_review`; hold statements moved back to `categorize_blocked`.

## 3. User Review

- For each statement at `categorize_review`, read the categorize artifact.
- Broker missing information, risky ambiguity, unresolved reconciliation findings, and manual extraction needs through the shared question contract.
- Batch compatible questions in the main thread; use fillable artifacts when provided.
- After answers, update the owning artifacts and status entries.
- Set `categorize_blocked` when review finds unresolved categorization or reconciliation input that needs a resumed categorize pass.
- Move resolved statements to `write_ready`.
- Gate: continue to write handoff only with statements at `write_ready`.
