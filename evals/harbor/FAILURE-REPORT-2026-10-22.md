# Harness compatibility fixes: job 2026-10-21__19-19-08

All three zero rewards came from trace checks. State checks passed in each
executed phase. The later approval, correction and stale-review steps did not
run. This change adapts the verifier to native harness evidence. It does not
change the harness, task prompts, financial checks, or approval requirements.

## Saved phase results

| Trial | Original state checks passed | Original trace failures | Trace replay |
| --- | ---: | ---: | --- |
| Init | Passed | 0 | 6/6 passed |
| Import review | 345 | 5 | 24/24 passed |
| Stale task initial review | 313 | 3 | 24/24 passed |
| Needs input | 77 | 7 | 25/25 passed |

Each executed phase's verifier directory under
[the saved job](../../.cache/harbor/jobs/2026-10-21__19-19-08/) now contains
`harness-trace-replay.json`. It records source session lines, evidence methods,
descendant identities and the original reward hash. Original rewards and
reports are unchanged. This replay reran trace checks only; state counts above
come from the original reports. It is not a new model run or an end-to-end pass.

## Verifier changes

- Accept invoked run-only launcher helpers and helpers with a positive timeout.
  Keep trusted launcher paths and terminal success requirements.
- Recover earlier reads in plain cat-only sequences from complete native output
  and operand diagnostics. Respect failed operands and `&&` short-circuiting.
- For bounded read-only `&&` chains, match complete file contents to the verifier
  bundle or saved ledger. This recovers the successful memory/schema reads before
  a trailing `rg` returned 1 in the needs-input trial.
- Keep descendant identity evidence separate from stage/group activity. Missing
  activity no longer implies that distinct workers were not spawned.
- Explain insufficient evidence in reports. Preserve fail-closed grading for
  unsupported code, unexecuted helpers, failed extraction and unrelated workers.

The import processor's successful CSV/PDF extractions were inside custom timeout
helpers. The correction checking processor used a simple run-only helper. The
stale categorizer and correction checking categorizer read their skills and
parsed documents in semicolon sequences. These are valid harness behaviors.

## Product findings and fixes

The saved import root session contains a skill-injection warning and an 8,159
character skill message including its wrapper. Its body ends partway through
the price instructions. Memory and final status instructions were omitted.
The source entrypoint was 9,141 bytes. Codex CLI 0.163.0 visibly clipped this
injection at about 8,000 characters; this is an observed pinned-version limit,
not a claim about every current Codex client.

Keep session creation, grouping, resume behavior, status ownership and panel
opening in `SKILL.md`. Shorten repeated wording across the entrypoint without
removing its action sequence or approval rules. The complete entrypoint is now
7959 bytes. The reference retains field definitions, schemas, examples and
validation semantics. A regression check protects the observed injection budget.
No model configuration or harness limit was raised.
The current [official skills documentation](https://developers.openai.com/codex/skills/)
recommends progressive disclosure, but describes the configurable initial skill
list budget separately; it does not establish the cause of this pinned CLI's
body clipping.

Processing also exposed two real gaps:

- `docling-tools` was rejected by the runtime whitelist. It now uses the same
  extraction environment as `docling`, including health checks. Process provides
  the supported model-download command, so workers need not find a versioned
  virtual environment themselves. The command is documented in the
  [Docling CLI reference](https://github.com/docling-project/docling/blob/main/docs/reference/cli.md)
  and the saved run includes successful direct use of the pinned binary.
- `timeout 60 auto_bean ...` failed with exit 127 because `auto_bean` is a shell
  function. Process now explains that an external timeout wraps the executable
  launcher. This fixes an actual execution mistake, not a verifier preference.

## Validation

- Full product and Harbor suite: 367 passed, one pre-existing failure.
- The failure is `test_native_harbor_config_defaults`: it expects one concurrent
  trial, while the checked-in configuration sets four. Configuration is unchanged.
- Focused runtime and trace tests: 111 passed.
- Ruff lint/format, Mypy (41 files), plugin package checks, and both changed skill
  validators passed.
- All four saved first-phase trace replays passed. No historical reward changed.
- No new model run, PDF model download, commit or push was performed.
