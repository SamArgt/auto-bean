# Structured state validation

Use the bundled validator before consuming parsed evidence, saving governed memory, or advancing import status. It checks versioned JSON Schemas plus cross-record IDs, safe workspace paths, and status transitions. It does not decide account identity, categorization, or user approval.

After resolving plugin/workspace paths and defining `auto_bean` from [plugin execution](plugin-execution.md):

```sh
auto_bean python "$AUTO_BEAN_PLUGIN/runtime/validate_state.py" parsed statements/parsed/example.json
auto_bean python "$AUTO_BEAN_PLUGIN/runtime/validate_state.py" memory .auto-bean/memory/category_mappings.json
auto_bean python "$AUTO_BEAN_PLUGIN/runtime/validate_state.py" status statements/import-status.yml --previous .auto-bean/tmp/status-before.yml
```

Import alone writes status. Capture the previous status index under `.auto-bean/tmp/`, merge only the returned statement update into the latest index, validate with `--previous`, and preserve unrelated entries/comments. Do not run status updates concurrently. `--approved <raw-path>` is permitted only when the user approved that statement's exact validated candidate; `--rework <raw-path>` only for explicit rework. These flags convey already-obtained authorization; they never grant it. Keep approval rationale in the import artifact, not in status.

Schemas live in [parsed](schemas/parsed.schema.json), [status](schemas/status.schema.json), and [memory](schemas/memory.schema.json) relative to this reference. Existing parsed version-1 documents without `schema_version` remain readable; new parsed outputs include `schema_version: 1` and `document_kind` (`statement` or `transaction_export`). Unknown versions block use. New or updated memory records have a stable `record_id`; add IDs to legacy records only when the memory skill next edits them, preserving their content and audit trail.

Parsed amounts are decimal strings, never floating-point numbers. IDs are unique within each document; every record references an account. Preserve source row identity across reparses; pair record IDs with the source fingerprint/account rather than a parse-run ID. Overlapping exports with different fingerprints still require external-ID or evidence-based duplicate review. Missing statement periods/balances are allowed for transaction exports; disclose checks as unavailable and obtain the required account/date interpretation instead of inventing balances.

Validate indexed import-source files individually after validating the index. Index paths are relative to `.auto-bean/memory/import_sources/`. Reject duplicate keys, escaping paths, symlinks, conflicting source/artifact pointers, invalid dates/amounts, duplicate IDs, and illegal transitions. On failure, report a bounded field/path error without dumping financial values; repair through the owning skill before downstream use.
