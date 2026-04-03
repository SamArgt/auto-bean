# Product Repo Agents

This repository authors the product, not a live user ledger workspace.

## Python Development
- Use `uv run` to run scripts and tools in the local environment.
- Use context7 mcp to look up documentation about external libraries and dependencies.

### After Code Changes
- Run `uv run ruff check` and `uv run ruff format` before committing changes.
- Use `uv run mypy` to check types when changing Python code.
- Use `uv run pytest` to run tests when changing Python code.
- Use `uv sync --group dev` to keep your local environment up to date with the latest dependencies and scripts.

## Development Boundaries

- Author skill behavior in `skill_sources/` first.
- Use the `skill-creator` system skill when creating or materially editing a skill.
- Treat `skill_sources/` as the source of truth for runtime skill content.
- Do not add live installed runtime skills under product-repo `.agents/skills/`.
- Keep `workspace_template/` focused on workspace skeleton, placeholders, and docs.
- Materialize authored skills into the user workspace during `auto-bean init`, not by hardcoding them into the template.

## Skills redaction guidelines
- Rely on the beancount online doc with the context7 MCP when redacting skills about beancount ledgers management.

## Code Boundaries

- Keep CLI surfaces thin and support-oriented.
- Put reusable orchestration in `src/auto_bean/application/`.
- Put side effects and copying/materialization logic in `src/auto_bean/infrastructure/`.
- Prefer changing markdown workflow behavior before adding new Python surfaces.

## Trust Model

- Codex skills are the primary user interface.
- Python helpers should support skill execution, validation, installation, and packaging.
- Avoid introducing CLI-first workflows when the architecture expects agent-led review and approval.

## Workspace Expectations

- User workspaces keep installed skills under `.agents/skills/`.
- User workspaces keep governed runtime state under `.auto-bean/`.
- Canonical ledger files remain in `ledger.beancount` and `beancount/`.
