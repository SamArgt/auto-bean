# Reading Parsed Statement JSON With jq

Parsed statement artifacts can be too large to read directly into the conversation. Use `jq` to inspect only the fields needed for the current decision, then load a small excerpt if it helps explain or verify the work.

Assume the assigned artifact is:

```sh
artifact="statements/parsed/checking-jan-2026.json"
```

## Quick Shape Checks

Confirm identity, parser, status, warnings, blockers, and record count:

```sh
jq '{
  parse_run_id,
  source_file,
  source_fingerprint,
  source_format,
  parser,
  status,
  parsed_at,
  warnings,
  blocking_issues,
  extracted_record_count: (.extracted_records // [] | length)
}' "$artifact"
```

Preview the first few normalized records without dumping the full artifact:

```sh
jq '.extracted_records[:5]' "$artifact"
```

List compact transaction rows for scanning:

```sh
jq -r '
  (.extracted_records // [])
  | .[]
  | [.record_id, .transaction_date, .description, .amount, .currency]
  | @tsv
' "$artifact"
```

## Targeted Lookups

Find records whose description mentions a term:

```sh
jq '
  (.extracted_records // [])
  | map(select((.description // "" | ascii_downcase) | contains("coffee")))
' "$artifact"
```

Find records in a date range:

```sh
jq '
  (.extracted_records // [])
  | map(select(.transaction_date >= "2026-01-01" and .transaction_date <= "2026-01-31"))
' "$artifact"
```

Find records by exact amount and currency:

```sh
jq '
  (.extracted_records // [])
  | map(select(.amount == "-4.50" and .currency == "EUR"))
' "$artifact"
```

Inspect raw field keys before relying on source-specific columns:

```sh
jq '
  (.extracted_records // [])
  | map(.raw_fields // {} | keys)
  | add
  | unique
' "$artifact"
```

## Pending Questions And Memory Suggestions

Show persisted questions without loading unrelated records:

```sh
jq '.pending_user_questions // []' "$artifact"
```

Summarize memory suggestions when present:

```sh
jq '
  (.memory_suggestions // [])
  | map({
      memory_type,
      decision,
      scope,
      confidence,
      review_state,
      supporting_evidence
    })
' "$artifact"
```

## Safe Reading Habits

- Do not paste or summarize the whole parsed artifact when it is long.
- Start with metadata, status, warnings, blockers, and record counts.
- Use filters for the specific record, date range, amount, source reference, or question being handled.
- Preserve `record_id`, `source_reference`, and source file context in any excerpt used for posting, clarification, deduplication, or reconciliation.
