# Import Discovery And Processing

Use for discovery, process sub-agent assignment, and process-question resolution.

1. Discover unprocessed work:
   - Use `git diff` to detect new or changed raw statements.
   - Read `statements/import-status.yml` through the shared status reference.
   - Create or update a status entry at `raw_ready` for each new, changed, missing-status, or explicitly reprocessable raw statement.
   - Create or refresh one import-owned artifact per raw statement under `.auto-bean/artifacts/import/`.
   - Use the same deterministic raw-statement filename prefix for process, categorize, and import artifacts.
   - Fingerprint supported raw files: `.pdf`, `.csv`, `.xlsx`, `.xls`.
   - Inspect `.auto-bean/memory/import_sources/index.json` and select only narrow matching `import_source_behavior` records by source identity, institution, account owner, account names, account hints, statement shape, filename pattern, or fingerprint.
   - Keep matched memory use consistent with the shared memory rules and record reuse attribution in the import-owned artifact.
   - Gate: continue to eligibility only after every discovered statement has a current status entry, or has been deliberately skipped with a reason.
2. Decide processing eligibility:
   - Send raw files to `$auto-bean-process` only when they have no current parsed output, missing status, changed fingerprint, `raw_ready` status, or an explicit user reprocess request.
   - Skip `done` entries unless the user explicitly requests rework; explicit rework sets the entry to `raw_ready` with the new reason recorded.
   - Keep current-fingerprint `process_blocked` entries with `process_attempts` of 2 or more out of automatic processing, preserve the last failure reason and process artifact, and surface the manual-resolution requirement.
   - Allow explicit user reprocess requests for held entries and record the new attempt reason without clearing prior history.
   - When a `process_blocked` entry is approved for reprocess, set it to `raw_ready` before assignment; when the blocker is manually resolved without reprocess, move it only to `process_review` or `account_review` if the process artifact and parsed evidence support that transition.
   - Gate: spawn processing only for statements at `raw_ready`; leave all others at their current review, blocked, done, or downstream status.
3. Spawn process sub-agents:
   - Spawn a sub-agent for each process-eligible statement.
   - Give each sub-agent the source path, current status entry, retry metadata, expected parsed-output path or naming rule, shared artifact prefix, selected `import_source_behavior` memory path or summary, and the instruction to use `$auto-bean-process`.
   - Require the process return schema.
   - Wait for all assigned process sub-agents before downstream parsed-statement handoff.
   - Gate: continue to process resolution only after every spawned sub-agent has returned `process_blocked`, `process_review`, or `account_review`.
4. Resolve process questions:
   - Inspect reported process artifacts.
   - For `process_review` or resolvable `process_blocked`, ask bounded questions needed to make parsed evidence trustworthy.
   - Record answers in the process artifact when they resolve or change parsed evidence.
   - Update the import-owned artifact with question ids, process artifact paths, affected paths, and resume decisions.
   - Resume `$auto-bean-process` only when parser-specific regeneration or normalization is required.
   - Move resolved `process_review` statements to `account_review`.
   - Keep unresolved statements at `process_review` or `process_blocked`; do not advance them to account inspection.
   - Gate: continue to account inspection only with statements at `account_review`.
