# Reading Import Status

Purpose: read and update `statements/import-status.yml` efficiently without turning it into a narrative artifact.

`statements/import-status.yml` is the operational index for import work. Each entry is keyed by raw statement path and should stay small: current status, source fingerprint, parsed statement path, stage artifact paths, timestamps, retry hold metadata, and compact booleans such as whether user input is required.

`ready` is a queue state, not a guarantee that the statement is processable. Before dispatch, check `manual_resolution_required`, `process_attempts`, and whether retry metadata applies to the current source fingerprint. A current-fingerprint `ready` entry with `manual_resolution_required: true` or retry attempts at the workflow threshold stays held until the user explicitly requests reprocess or supplies missing evidence.

## Status Table

| status | owner next action | blocked by |
| --- | --- | --- |
| `ready` | queue state; `$auto-bean-import` may assign `$auto-bean-process` only after retry metadata checks | missing parser-ready evidence, `manual_resolution_required`, or manual retry hold |
| `parsed` | `$auto-bean-import` moves to `account_inspection` | none unless process artifact says otherwise |
| `parsed_with_warning` | `$auto-bean-import` reviews process artifact and resolves warnings | unresolved process warning or question |
| `account_inspection` | `$auto-bean-import` derives first-seen account structure | unclear account identity, currency, or mutation target |
| `balance_check` | `$auto-bean-import` verifies opening balances against ledger | balance discrepancies |
| `ready_for_categorization` | `$auto-bean-import` assigns `$auto-bean-categorize` | none |
| `ready_for_review` | `$auto-bean-import` reviews categorize artifact and collects needed user input | unresolved categorize, reconciliation, duplicate, or transfer decision |
| `ready_to_write` | `$auto-bean-import` invokes `$auto-bean-write` | none |
| `final_review` | `$auto-bean-import` asks the user to approve final import result | user approval |
| `done` | no action unless the user requests rework | complete |

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
- If two entries point to the same raw statement, parsed statement, or stage artifact incompatibly, fail closed and surface the conflict instead of choosing one silently.
