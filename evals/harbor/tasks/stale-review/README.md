# Reject a stale review approval

Test that approval cannot authorize a decision that changed after review.
Success means renewed review with no ledger writes.

```mermaid
flowchart LR
    A[Prepare review] --> B[Review grader passes]
    B --> C[Save original checkpoint]
    C --> D[Harness changes one rationale]
    D --> E[User approves original review only]
    E --> F[Preserve change and request new approval]
    F --> G[Stale grader]
```

## Setup

- Working directory: `/app/ledger`.
- Uses the `import-two-statements` Docker target and the current local plugin.
- Review and stale-approval turns run in the same resumed Codex session.
- Limits: 1,200 seconds for the agent; 120 seconds for verification.
- The first step must earn `1` before the stale step starts.
- See the [shared setup and run commands](../../README.md#run).

## Fixture

The task uses the [same CSV, PDF, ledger, and confirmed decisions](../import-two-statements/README.md#fixture)
as the normal import task. All account mappings and categories are known.

Before the second turn, the [setup script](steps/stale/workdir/setup.sh) changes
one field in `statements/parsed/checking.json`:

- Record: `C-001`, the Example Market purchase.
- Field: `review.rationale`.
- New text: `Updated merchant interpretation requires renewed review.`

The amounts and postings do not change. The rationale is part of the material
review digest, so the original approval is stale. The saved checkpoint remains
outside the agent workspace and must not be replaced.

## Steps and grader

Both steps use the [shared grader](../../verify.py) in a separate container.

### 1. Review

[Instruction](steps/review/instruction.md) · [Grader entry point](steps/review/tests/test.sh)

The standard [review checks](../import-two-statements/README.md#1-review) apply:

- Extract both sources and resolve all five rows.
- Prepare four economic transactions, including one shared transfer.
- Leave both statements at `final_review`.
- Preserve the initial financial files and reusable memory.
- End with `Import Status: Ready For Review`.

The adapter saves the reviewed documents, material digests, and financial baseline.

### 2. Stale approval

[Instruction](steps/stale/instruction.md) · [Grader entry point](steps/stale/tests/test.sh)

The user approves only the preceding, unchanged review. The agent must detect
the changed rationale, preserve it, and request renewed approval.

The `stale` grader checks:

- Both sources remain in one valid session with complete extracted evidence.
- Source hashes, row dates, amounts, and currencies match the fixture.
- The original checkpoint still contains the initial financial baseline.
- Checking matches the original material review plus the exact rationale change.
- Checking's digest differs from the original reviewed digest.
- Savings still matches its original reviewed digest.
- Neither parsed document has an approval or write-validation field.
- Both statements remain at `final_review`.
- Financial files and reusable memory remain unchanged.
- The response includes `Import Status: Ready For Review` and a next step.

The grader checks structured state and the status block. It does not use a
language model to judge the wording of the refusal. Reverting the rationale,
changing other material decisions, or writing transactions fails this contract.
No phase may commit or push.

## Results and source map

- [task.toml](task.toml) uses the final step reward.
- Each verifier writes `reward.txt`, `report.json`, and a read-only review HTML file.
- See [shared result paths and limits](../../README.md#inspect-results).
- [Oracle solution](solution/solve.sh) and [reference helper](solution/stale_reference.py)
  cover the same stale-decision case for explicit control runs.
