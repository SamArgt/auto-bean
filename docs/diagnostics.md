# Diagnostics and Artifacts

`auto-bean` now persists structured workflow diagnostics under `.auto-bean/artifacts/`.

Each blocked or completed workflow run writes a JSON artifact with:

- a stable `run_id`
- the workflow name and creation timestamp
- structured result data, including error classification
- ordered workflow stage events for troubleshooting

These artifacts are governed runtime state, not source files or user-owned ledger data. They are intentionally kept outside `src/`, `docs/`, and future ledger workspaces.

## Troubleshooting intent

Use the latest artifact when you need to inspect why a workflow passed, failed, or stopped safely:

- prerequisite failures explain missing tools or unsupported environments
- blocked mutation results make reserved or unsafe flows explicit
- execution errors capture runnable-but-broken states without relying on raw stack traces

For CI parity, run the same baseline checks locally:

```bash
uv sync --group dev
uv run ruff check src tests scripts
uv run mypy src tests scripts
uv run pytest
uv run python scripts/run_smoke_checks.py
```
