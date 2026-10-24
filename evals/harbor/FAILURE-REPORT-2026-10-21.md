# Investigation: Harbor job 2026-10-21__18-24-47

All four trials received reward `0`. These results do not show four broken
ledger workflows. The saved evidence shows stale state rules, trace-reader
coverage gaps, and two missing initialization reads.

This investigation uses the saved workspaces, runtime records, native sessions,
and verifier reports. It does not rerun the model or change the historical
rewards. Later workflow steps were not reached.

## Results by task

| Trial | Last executed phase | Original state result | Original trace checks | Main finding |
| --- | --- | --- | --- | --- |
| `init-ledger__guimWhX` | Init | Passed | 2 passed, 4 failed | Valid initialized workspace. Two required content reads are absent; two other actions are excluded by shell parsing. |
| `import-two-statements__jJ3aGx7` | Review | Failed | 15 passed, 6 failed | Grader rejects document directives required by the current skill. Trace reader misses recorded worker and helper commands. |
| `stale-review__pfGAKKz` | Review | Failed | 15 passed, 6 failed | Same directive mismatch. The stale-approval phase never ran. |
| `human-input-correction__TVoxxJq` | Needs input | Failed | 6 passed, 14 failed | Grader rejects a real failed review validation and later looks up the wrong account ID. Correction and approval never ran. |

Original reports and all linked evidence are under
[the saved job](../../.cache/harbor/jobs/2026-10-21__18-24-47/).
For multi-step trials, phase artifacts are in `steps/<phase>/`; init artifacts
are directly under its trial directory.

## State findings

### Import and stale review: a rule conflicts with the skill

`import_checks()` requires every account's `proposed_directives` to be empty.
Its error says “Fixture needs no new account or balance directives”, but the
condition rejects every directive type, including `document`.

The import trial proposes only these two directives:

```beancount
2026-01-31 document Assets:Checking "statements/raw/checking.csv"
2026-01-31 document Assets:Savings "statements/raw/savings.pdf"
```

The stale-review trial proposes the same documents and two balance assertions:

```beancount
2026-02-01 balance Assets:Checking 870.00 EUR
2026-02-01 balance Assets:Savings 602.00 EUR
```

These remain proposals in parsed JSON. They were not written to the ledger.
The [import skill](../../plugins/auto-bean/skills/auto-bean-import/SKILL.md)
requires a document directive per mapped account. The
[import contract](../../plugins/auto-bean/references/import-review.md)
also permits justified balance assertions. The saved closing balances support
these amounts. No new account or opening adjustment is proposed.

Evidence: each trial's
`steps/review/artifacts/app/ledger/statements/parsed/january-accounts.json` and
`steps/review/artifacts/opt/eval-evidence/last-response.txt`.

For diagnosis only, I repeated state checks with this one assertion recorded
but allowed to continue. Both trials completed all 255 executed assertions:
253 passed and the same directive assertion failed once for each statement.
This checks the remaining transaction, provenance, transfer, checkpoint,
memory, response, and runtime requirements. It is not an official pass or a
replacement grading policy. The current renderer does not independently
validate the proposed supporting directives; a corrected grader must do so.

### Needs input: review validation is mislabeled as fabricated writing

`scenario_checks()` rejects the presence of any `review.validation` field.
Both saved records instead contain genuine failed review-stage validation:

| Source | Stage | State | Error |
| --- | --- | --- | --- |
| Checking | `review` | `failed` | Every extracted record needs a resolved disposition. |
| Savings | `review` | `failed` | Every extracted account needs a resolved mapping. |

The agent ran the validator. It returned exit code `1` and these errors. The
final response says review validation is blocked. Neither record claims
successful writing, and both have empty ledger hashes and zero checked rows.
The label “Fabricated write validation” is therefore unsupported by this
evidence. The shared validation contract explicitly separates `review` and
`written` stages and permits reporting pending members.

Diagnostic continuation exposed another mismatch. The grader looks up the
literal account ID `savings`. The extracted account uses `SAVINGS-TEST`, which
is schema-valid and matches the source. Its review has `state: needs_input`
and two explicit mapping suggestions. The grader's fixed lookup returns an
empty object and reports “Missing unresolved account suggestions”.
`correction_checks()` also hardcodes `savings`, so the same assumption would
affect a later correction phase.

After recording and bypassing only these two conditions in a temporary
diagnostic process, all 73 assertions ran: 70 passed; the validation-presence
check failed twice and the fixed-ID lookup failed once. The unresolved
category, hold disposition, suggestions, response, memory boundary, and
unchanged financial files passed their remaining checks.

Evidence: `human-input-correction__TVoxxJq/steps/needs-input/artifacts/`:

- `app/ledger/statements/parsed/january-2026-own-accounts.json`.
- `opt/eval-evidence/last-response.txt`.
- The completed validation command in `logs/agent/codex.txt` reports the same
  errors and timestamp, `2026-10-21T16:35:23Z`.

### Initialization: valid state, missing inspection evidence

All original init state checks passed. They include a valid empty EUR ledger,
default accounts, complete scaffold, one clean local commit, no copied product
runtime, and managed-runtime validation.

The native trace does not contain content reads of `ledger.beancount` or
`.auto-bean/workspace.json`. Those are genuine gaps against the evaluation's
explicit trace contract. Successful initialization and validation do not satisfy
those separate read requirements.

The init skill read and `git status` are present in shell calls, but precede
other commands. The conservative parser drops them. A zero exit code for the
whole shell call does not separately prove every earlier command succeeded.

## Trace findings shared across trials

### Child-session metadata mismatch

The pinned CLI records descendant sessions with
`source.subagent.thread_spawn.parent_thread_id`. `load_commands()` only checks
`source.subagent.spawn.parent_thread_id`. Consequently it excludes all saved
child sessions. The logs are present: two children for import, two for stale
review, and three for correction. Delegation did occur.

### Successful commands outside the parser's supported forms

- All three import processors ran Docling on both original sources with
  `timeout 60 sh ...` or `timeout 120 sh ...`. The completion events report
  success. `operation()` does not unwrap `timeout`.
- The import root defines and invokes the documented `auto_bean()` shell
  helper on the same line. Query and review-validation commands completed
  successfully, but `shell_commands()` ignores function-definition lines.
- A semicolon before a launcher command discards the preceding variable
  assignment. This prevents recognition of a stale-review extraction setup
  command that completed successfully.
- Earlier commands in semicolon or multiline calls, and pipeline-containing
  lines, are deliberately excluded. Their text and output can show attempted
  reads, but the shell exit code alone does not prove individual success.
  Reports should distinguish uncredited evidence from actions never attempted.

### Delegation coverage is silently omitted after state failure

The original verifier derives stage groups only after all state checks pass.
Because these three import-related trials fail state checks first, their trace
reports omit the group/stage worker checks entirely. Their trace counts must
not be interpreted as complete delegation coverage.

### Native evidence index

Paths below are relative to each executed phase's `agent/sessions/2026/10/21/`.
Line numbers identify native JSONL events. Each file's first line also records
its parent metadata.

| Trial / session filename | Lines | Evidence |
| --- | --- | --- |
| Init: `rollout-2026-10-21T16-29-37-01a15f4b-fa67-7320-a3ed-31f4dd0756c2.jsonl` | 17, 32 | Init skill read and Git status before later shell commands. |
| Import worker: `rollout-2026-10-21T16-30-31-01a15f4c-cf70-71b1-a344-bf879183b35a.jsonl` | 25, 43, 98, 113 | Group schema, extraction setup, CSV and PDF extraction. |
| Import root: `rollout-2026-10-21T16-29-37-01a15f4b-f993-7283-af3d-f0648f63a070.jsonl` | 70, 82, 252 | Queries and review validation through inline shell helper. |
| Stale worker: `rollout-2026-10-21T16-30-22-01a15f4c-abe6-79c3-9dd4-7301177ae3f2.jsonl` | 20, 25, 45, 111, 121 | Process skill, group schema, extraction setup, both extractions. |
| Stale categorizer: `rollout-2026-10-21T16-33-03-01a15f4f-1e04-7892-bb28-13f53522db96.jsonl` | 48 | Ledger and account reads. |
| Correction root: `rollout-2026-10-21T16-29-37-01a15f4b-f9a4-7931-bed2-491aac0514c3.jsonl` | 18, 23, 30, 68, 79 | Skill, context, schema and ledger reads in compound shell calls. |
| Correction worker: `rollout-2026-10-21T16-30-42-01a15f4c-f994-7d03-a9b4-73f094f36564.jsonl` | 25, 40, 114, 127 | Group schema, extraction setup, both extractions. |

## Verified preservation and limits

I regenerated the deterministic synthetic baseline from the current fixture
code. Its commit is `6da70a9feb2b3d5e4ec04430e05b69b182584986`, matching the
saved import workspaces. Raw hashes and protected-file checks passed.
All three import-related workspaces retain exactly the original financial
file hashes. Their saved runtime records each report `runtime_present: true`
and `validated: true`. No premature financial writing was found.

No approval, correction, completed import, or stale-approval rejection was
tested after the failed first-step reward gates. These later behaviors remain
unverified by this job. Diagnostic continuation does not establish a full
trace pass or an end-to-end task pass.

## Delivered diagnostic artifacts

The verifier now writes `report.md` and a versioned `report.json` with individual
executed checks, counts, source locations, selected observed values, and explicit
skipped groups. It retains the existing scoring rules. A skipped group is not
an individual check count. State grading still stops at its first failure.

I replayed all four saved phases with the new reporter and the unchanged grading
rules. Each replay matched the original state verdict, trace verdict, failure,
policy, and overall verdict. The original `report.json` and `reward.txt` remain
unchanged. In each existing verifier directory, open these added files:

- `diagnostic-report.md`: readable check results.
- `diagnostic-report.json`: structured results and replay provenance.

Harbor 0.24's installed viewer renders Markdown and displays HTML as source.
The Markdown preview was checked in the running viewer. Refresh the trial page
to discover the added diagnostic files. Future verifier runs write `report.md`
and `report.json` automatically. The `diagnostic-` names identify the offline
replays added to this historical job. SVG output was removed at the user's request.

| Trial | Executed state assertions passed | Failed | Skipped state groups |
| --- | ---: | ---: | ---: |
| Init | 119 | 0 | 0 |
| Import | 45 | 1 | 1 |
| Stale review | 45 | 1 | 1 |
| Needs input | 48 | 1 | 1 |

The import-related reports also mark state-dependent trace expectations skipped.
The counts include file guards and schema checks; they are not counts of unique
business requirements. They differ from the diagnostic-continuation counts
above because normal grading stops early and the new reporter also records
successful schema/session checks.

Validation of the reporting change:

- Ruff lint and format checks passed.
- Mypy passed for all 41 configured source files.
- Product and Harbor tests: 289 passed, one failed. The failure is the existing
  default-config test: the user's local `codex.yaml` sets four concurrent trials,
  while the test expects one. That pre-existing edit was preserved.
- Plugin package validation passed.
- All four offline replays preserved the original verdicts and rewards.

## Fixes implemented after this investigation

The following changes are now implemented locally:

- The verifier parses proposed documents and optional exact closing assertions.
  It requires one document per source, renders the proposals independently for
  review, and checks the same directives in the approved ledger. Other targets,
  dates, currencies, amounts, tolerances, duplicate documents, and directive
  types fail. Oracle solutions now propose and write the required documents.
- Needs-input checks accept failed current review validation for unresolved
  choices. Written-stage results, stale digests, and false readiness claims fail.
  Account decisions use the sole extracted account rather than a fixed local ID.
- Trace parsing recognizes both parent metadata formats, plain positive timeout
  wrappers, unconditional launcher assignments, and the exact documented helper
  in inline or multiline form. Arbitrary helpers and ambiguous earlier commands
  remain uncredited. Command-prefix environment variables do not leak into later
  commands during analysis.
- Init now explicitly inspects the generated ledger, marker, and Git status.
  Common guidance requests separate shell calls or `&&` chains for required reads
  and workflow checks, so individual failures cannot be hidden by later success.
- Task versions are now 2.1.0 for init/import and 3.1.0 for correction/stale review.
  Regression tests cover the accepted cases and invalid or forged alternatives.

Replaying only the saved first phases with the corrected verifier gives:

| Saved phase | State | Trace | Remaining uncredited trace requirements |
| --- | --- | --- | --- |
| Import review | Pass | 24/24 pass | None |
| Stale task's initial review | Pass | 24/24 pass | None |
| Needs input | Pass | 20/23 pass | Import skill and session/status schema reads precede later commands in compound calls. |
| Init | Pass | 2/6 pass | Skill read and Git status precede later commands; ledger and marker content reads are absent. |

Each historical verifier directory now contains `fixed-verifier-report.md` and
`fixed-verifier-report.json` for this comparison. The original reports, original
diagnostic reports, and rewards are unchanged. A fresh model run is still needed
to exercise the amended skill guidance and all later phases. No new Harbor model
run was started as part of these code changes.

Validation of the implemented fixes:

- Full test suite: 332 passed, one failed. The existing default-config test
  expects one concurrent trial; the user's preserved local configuration sets four.
- Ruff lint and format checks, Mypy, plugin packaging, and init skill validation
  passed.
- The final focused trace suite passed all 62 tests.

## Original recommended follow-up fixes

1. Replace the blanket directive ban with semantic checks for the expected
   source documents and permitted closing assertions. Continue rejecting
   invented accounts and opening adjustments. Include supporting directives
   in independent review rendering and approved-ledger checks.
2. Distinguish generated review failure from fabricated or premature written
   validation. Resolve account decisions through source identity instead of
   fixture-local IDs in both needs-input and correction checks.
3. Support the pinned CLI's descendant metadata and safe timeout wrappers.
   Test the documented launcher helper. Keep ambiguous compound-shell evidence
   uncredited unless individual success can be established.
4. Make init inspect its generated ledger and workspace marker explicitly.
5. After those changes, run the four tasks again. This remains pending an explicit
   request for a fresh Harbor model run. Historical rewards remain unchanged.
