# Workspace Agents

This ledger workspace is prepared for Codex-driven workflows.
This workspace is initialized as a Git repository during `auto-bean init`.

- Keep product-code changes in the `auto-bean` product repository.
- Keep runtime ledger data, statements, and generated artifacts inside this workspace.
- Use Git in this workspace to inspect diffs, review history, and create approved commits.
- Review structural ledger changes before accepting them into the ledger.
- Use the installed skill under `.agents/skills/auto-bean-apply/` as the primary workflow surface.
- Do not commit changes to `ledger.beancount` or `beancount/` until the user has explicitly approved the validated proposal.
