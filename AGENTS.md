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

- Author skill behavior in `plugins/auto-bean/skills/` first.
- Use the `skill-creator` system skill when creating or materially editing a skill.
- Treat `plugins/auto-bean/skills/` as the source of truth for runtime skill content.
- Treat `auto-bean-query` and `auto-bean-write` as foundation skills that higher-level workflows may rely on for read-only ledger analysis and transaction writing.
- Do not add live installed runtime skills under product-repo `.agents/skills/`.
- Keep `plugins/auto-bean/assets/workspace_template/` focused on workspace skeleton, placeholders, and docs.
- Distribute the plugin directory directly. Never copy product skills or helpers into ledger workspaces.

## Skills redaction guidelines
- Rely on the beancount online doc with the context7 MCP when redacting skills about beancount ledgers management.

## Repo Structure

- Keep bundled Python helpers under `plugins/auto-bean/runtime/auto_bean/`.
- Use the noninteractive plugin launcher for initialization, migration, and runtime tools.
- Keep the root Python environment limited to development tools; lock released ledger dependencies in the plugin runtime project.
- Add new modules only when they clearly improve readability or separate a real independent concern.

## Code Boundaries

- Keep CLI surfaces thin and support-oriented.
- Separate initialization, migration, and runtime preparation where they own independent concerns.
- Prefer changing markdown workflow behavior before adding new Python surfaces.
- For direct ledger-mutation workflows, present review details directly in the agent conversation; do not add separate mutation artifact requirements in the product repo.

## Trust Model

- Codex skills are the primary user interface.
- Narrow foundation skills own ledger-specific mechanics: `auto-bean-query` for read-only Beancount analysis and `auto-bean-write` for transaction drafting, validation, and transaction-specific clarification.
- Orchestration skills such as `auto-bean-import` and `auto-bean-categorize` should rely on those foundation skills when they need ledger reads or transaction-writing inputs.
- Python helpers should support skill execution, validation, installation, and packaging.
- Avoid introducing CLI-first workflows when the architecture expects agent-led review and approval.

## Workspace Expectations

- User workspaces use installed plugin skills; they do not contain copied product skills.
- Treat legacy skill retirement as a reviewed migration with backups, not broad stale-file deletion.
- User workspaces keep governed runtime state under `.auto-bean/`.
- Canonical ledger files remain in `ledger.beancount` and `beancount/`.
