# Product Repo Agents

This repository authors the product, not a live user ledger workspace.

## Development Boundaries

- Author skill behavior in `skill_sources/` first.
- Use the `skill-creator` system skill when creating or materially editing a skill.
- Treat `skill_sources/` as the source of truth for runtime skill content.
- Do not add live installed runtime skills under product-repo `.agents/skills/`.
- Keep `workspace_template/` focused on workspace skeleton, placeholders, and docs.
- Materialize authored skills into the user workspace during `auto-bean init`, not by hardcoding them into the template.

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
