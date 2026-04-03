# Workspace Guide

Use this workspace as the runtime home for your personal ledger.

The workspace starts as a Git repository with an initial commit for the generated scaffold.

Validation:

```bash
./scripts/validate-ledger.sh
```

Inspection:

```bash
./scripts/open-fava.sh
```

Structural review:

1. Use `.agents/skills/auto-bean-apply/` so the coding agent summarizes the change in ledger context.
2. Ask for a proposal document only when the user wants deeper inspection or the change is risky.
3. Validate the workspace before approval and commit only after explicit approval.

Governed review artifacts live under `.auto-bean/proposals/` and `.auto-bean/artifacts/`.
