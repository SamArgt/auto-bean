# Reading Import Status

Purpose: read and update `statements/import-status.yml` efficiently without turning it into a narrative artifact.

`statements/import-status.yml` is the per-statement operational index for import work. Each entry is keyed by raw statement path and should stay small: current status, source fingerprint, parsed statement path, stage artifact paths, timestamps, retry hold metadata, and compact booleans such as whether user input is required.

Statuses describe one statement's next owner action. A batch import may contain statements in many statuses at the same time; `$auto-bean-import` should advance each eligible statement independently while preserving cross-statement review before writing.

## Single-Statement Status Machine

| status | owner next action | normal next status | hold or retry condition |
| --- | --- | --- | --- |
| `raw_ready` | `$auto-bean-import` may assign `$auto-bean-process` | `process_blocked`, `process_review`, or `account_review` | Hold only when processing cannot be assigned safely. |
| `process_blocked` | `$auto-bean-import` surfaces parser/manual-resolution blocker | `raw_ready` for explicit reprocess, or `process_review`/`account_review` if the blocker is resolved without reprocess | Stay blocked until the user supplies missing evidence, approves reprocess, or accepts a manual resolution. |
| `process_review` | `$auto-bean-import` reviews process artifact | `account_review` | Stay in review while process warnings or process questions are unresolved. |
| `account_review` | `$auto-bean-import` inspects accounts | `balance_review` | Move to `account_blocked` if account identity, currency, duplicate risk, mutation target, or account-opening approval is unresolved. |
| `account_blocked` | `$auto-bean-import` asks account-structure question | `balance_review` | Stay blocked until account questions are answered and any approved account directives are written and validated. |
| `balance_review` | `$auto-bean-import` checks opening balances | `categorize_ready` | Move to `balance_blocked` if statement opening balance and ledger balance disagree or the check cannot be trusted. |
| `balance_blocked` | `$auto-bean-import` asks balance-remediation question | `categorize_ready` | Stay blocked until the user chooses a remediation path and any approved ledger edit is written and validated. |
| `categorize_ready` | `$auto-bean-import` may assign `$auto-bean-categorize` | `categorize_blocked` or `categorize_review` | Hold only when categorization cannot be assigned safely. |
| `categorize_blocked` | `$auto-bean-import` brokers categorize clarification | `categorize_review` after the resumed categorize stage persists resolved work | Stay blocked while categorization, reconciliation, duplicate, transfer, or manual source interpretation is unresolved. |
| `categorize_review` | `$auto-bean-import` reviews categorize artifact and batch findings | `write_ready` | Move to `categorize_blocked` if review finds unresolved categorization or reconciliation input. |
| `write_ready` | `$auto-bean-import` may invoke `$auto-bean-write` | `write_blocked` or `final_review` | Hold only when writing cannot be assigned safely. |
| `write_blocked` | `$auto-bean-import` brokers write-stage clarification or fix | `final_review` after the resumed write stage validates | Stay blocked while transaction facts, duplicate/transfer risk, validation, or write evidence is unresolved. |
| `final_review` | `$auto-bean-import` asks the user to approve final import result | `done` | Stay in final review until the user approves that statement's final import result. |
| `done` | no action unless the user requests rework | `raw_ready` only for explicit rework/reprocess | No automatic transition. |

Allowed sub-agent status updates:

- `$auto-bean-process`: `process_blocked`, `process_review`, or `account_review`.
- `$auto-bean-categorize`: `categorize_blocked` or `categorize_review`.
- `$auto-bean-write`: `write_blocked`, or `final_review` only after the import-invoked write validates.
- `$auto-bean-import`: all orchestration transitions, including blocked-state resolution and `done`.

When the file is large:

- Search by exact raw path first, then read only that entry.
- Use `rg -n "statements/raw/...|current_status:|parsed_statement:|artifacts:" statements/import-status.yml` to find nearby lines quickly.
- Use a YAML parser for edits or audits; avoid broad text rewrites that could move unrelated statement entries.
- Treat `parsed_statement` as evidence under `statements/parsed/`, not a workflow artifact.
- Treat `artifacts.process`, `artifacts.categorize`, and `artifacts.import` as pointers to stage-owned review/provenance files under `.auto-bean/artifacts/`.
- Keep detailed warnings, questions, answers, and decision rationale in the referenced artifacts; status stores only pointers and compact operational flags.

Recovery:

- If YAML is malformed, has duplicate keys, has path conflicts, or cannot be parsed without losing comments or unrelated entries, stop before editing and report the affected path or line when known.
- If an entry has an unknown status, keep it out of automatic dispatch and ask `$auto-bean-import` or the user to resolve the status.
- If two entries point to the same raw statement, parsed statement, or stage artifact incompatibly, apply the shared fail-closed invariant and surface the conflict instead of choosing one silently.
