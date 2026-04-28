# Reading Parsed Statement JSON With jq

Parsed statement JSON files can be too large to read directly into the conversation. Use `jq` to inspect only the fields needed for the current decision, then load a small excerpt if it helps explain or verify the work.

Assume the assigned parsed statement is:

```sh
parsed="statements/parsed/checking-jan-2026.json"
```

## Quick Shape Checks

Confirm identity, parser metadata, process artifact pointer, and record count:

```sh
jq '{
  parse_run_id,
  source_file,
  source_fingerprint,
  source_format,
  parser,
  parsed_at,
  process_artifact,
  extracted_record_count: (.extracted_records // [] | length)
}' "$parsed"
```

Preview the first few normalized records without dumping the full parsed statement:

```sh
jq '.extracted_records[:5]' "$parsed"
```

List compact transaction rows for scanning:

```sh
jq -r '
  (.extracted_records // [])
  | .[]
  | [.record_id, .transaction_date, .description, .amount, .currency]
  | @tsv
' "$parsed"
```

## Targeted Lookups

Find records whose description mentions a term:

```sh
jq '
  (.extracted_records // [])
  | map(select((.description // "" | ascii_downcase) | contains("coffee")))
' "$parsed"
```

Find records in a date range:

```sh
jq '
  (.extracted_records // [])
  | map(select(.transaction_date >= "2026-01-01" and .transaction_date <= "2026-01-31"))
' "$parsed"
```

Find records by exact amount and currency:

```sh
jq '
  (.extracted_records // [])
  | map(select(.amount == "-4.50" and .currency == "EUR"))
' "$parsed"
```

Inspect raw field keys before relying on source-specific columns:

```sh
jq '
  (.extracted_records // [])
  | map(.raw_fields // {} | keys)
  | add
  | unique
' "$parsed"
```

## Safe Reading Habits

- Do not paste or summarize the whole parsed statement when it is long.
- Start with metadata and record counts.
- Use filters for the specific record, date range, amount, or source reference being handled.
- Preserve `record_id`, `source_reference`, and source file context in any excerpt used for posting, clarification, deduplication, or reconciliation.
- Read warnings, blockers, questions, answers, memory suggestions, and review notes from the referenced individual process, categorize, or import artifacts. Parsed statement JSON should only point to those artifacts, not duplicate their warning, question, or answer payloads.
