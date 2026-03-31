# auto-bean

`auto-bean` is a packaged Python foundation for local-first coding-agent workflows around Beancount ledgers.

This story establishes only the initial application skeleton:

- packaged `src/auto_bean/` layout
- baseline CLI entrypoint
- architecture-aligned layer packages for future stories
- top-level test placement under `tests/`

Repo boundary notes for future maintainers:

- application code belongs under `src/auto_bean/`
- stable user-owned ledger, memory, and artifact state must stay out of `src/`
- top-level `scripts/` remains reserved for repo helper tooling
- `.agents/skills/` remains the home for installed skill surfaces
- future governed runtime state belongs under `.auto-bean/`, not inside the package tree

Bootstrap/readiness flows, dependency setup, CI, and ledger workspace creation are intentionally deferred to later stories.
