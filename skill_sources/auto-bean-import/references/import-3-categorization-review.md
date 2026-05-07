# Import Categorization Review

Use for categorization sub-agent handoff, cross-statement review, and user review before writing.

## 1. Categorization Handoff

- For each statement at `categorize_ready`, spawn a sub-agent for that parsed statement and instruct it to use `$auto-bean-categorize`.
- Require the categorize return schema.
- Keep statements with clarification, repair, or manual source blockers at `categorize_blocked` and out of posting and final approval.
- Gate: continue to cross-statement review only after ALL categorize sub-agents have returned `categorize_review` or `categorize_blocked` and close categorize sub-agents.

## 2. Cross-Statement Review

- Before surfacing categorize findings, read categorize artifacts and posting inputs for statements in the same batch that reached `categorize_review` or `categorize_blocked`.
- Compare candidates for likely transfers, duplicates, mirror-image amounts, nearby dates, matching currencies, complementary descriptions, shared references, fees, FX legs, and account-pair patterns.
- Use `$auto-bean-query` for existing ledger activity when needed.
- Record only reviewable candidates; do not auto-drop, auto-net, or silently mark duplicates without strong current evidence or approved user input.
- When a likely transfer or duplicate spans artifacts, update each categorize artifact with a labeled `Import Batch Cross-Statement Review` section and update import-owned artifacts with links, ids, summaries, and posting impact.

## 3. User Review

- For each statement at `categorize_review` or `categorize_blocked`, read the categorize artifact.
- For `categorize_blocked` statements, broker missing information, risky ambiguity, unresolved reconciliation findings, and manual extraction needs through the shared question contract.
- Batch compatible questions in the main thread; use fillable artifacts when provided.
- After answers, update both the categorize artifact and the import-owned artifacts and status entries.
- Move resolved statements to `write_ready`.
- Gate: continue to write handoff only if ALL statements are at `write_ready`. Wait for user answers for `categorize_blocked` or `categorize_review` statements before advancing to write handoff.
