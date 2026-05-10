# Import Discovery And Processing

Use for discovery, process sub-agent assignment, and process-question resolution.

1. Discover unprocessed work:
   - Use `git status --short` to detect new or changed raw statements.
   - Read `statements/import-status.yml` through the shared status reference.
   - Create or update a status entry at `raw_ready` for each new, changed, missing-status, or explicitly reprocessable raw statement.
   - Create or refresh one import-owned artifact per raw statement under `.auto-bean/artifacts/import/`.
   - Use the same deterministic raw-statement filename prefix for process, categorize, and import artifacts.
   - Fingerprint supported raw files: `.pdf`, `.csv`, `.xlsx`, `.xls`.
   - Inspect `.auto-bean/memory/import_sources/index.json` and select only narrow matching `import_source_behavior` records by source identity, institution, account owner, account names, account hints, statement shape, filename pattern, or fingerprint.
   - Keep matched memory use consistent with the shared memory rules and record reuse attribution in the import-owned artifact.
   - Gate: continue to process sub-agent assignment only after all raw statements are at `raw_ready` and import-owned artifacts are created or updated.
2. Spawn process sub-agents with `$auto-bean-process`:
   - Spawn a sub-agent for each process-eligible statement.
   - Give each sub-agent relevant `.auto-bean/memory/MEMORY.md` context, the source path, current status entry, retry metadata, expected parsed-output path or naming rule, shared artifact prefix, selected `import_source_behavior` memory path or summary, and the instruction to use `$auto-bean-process`.
   - Require the process return schema.
   - Wait for all assigned process sub-agents before downstream parsed-statement handoff.
   - Gate: continue to process resolution only after every spawned sub-agent has returned `process_blocked`, `process_review`, or `account_review`.
3. Resolve process questions:
   - Inspect reported process artifacts.
   - For `process_review` or resolvable `process_blocked`, ask bounded questions needed to make parsed evidence trustworthy.
   - Record answers in the process artifact when they resolve or change parsed evidence.
   - Update the import-owned artifact with question ids, process artifact paths, affected paths, and resume decisions.
   - Resume `$auto-bean-process` only when parser-specific regeneration or normalization is required.
   - Move resolved `process_review` statements to `account_review`.
   - Keep unresolved statements at `process_review` or `process_blocked`; do not advance them to account inspection.
   - Gate: continue to account inspection only if ALL statements are at `account_review`. Wait for user answers for `process_blocked` or `process_review` statements before advancing to account inspection.
