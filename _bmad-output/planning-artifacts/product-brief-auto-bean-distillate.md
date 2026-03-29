---
title: "Product Brief Distillate: auto-bean"
type: llm-distillate
source: "product-brief-auto-bean.md"
created: "2026-03-29T14:18:18Z"
purpose: "Token-efficient context for downstream PRD creation"
---

# Product Brief Distillate: auto-bean

## Product Intent

- `auto-bean` is a local-first, open source repo template that equips coding agents such as Codex with a complete skill set for operating Beancount ledgers.
- The product is explicitly agent-first: the intended interface is a terminal workflow or agent app, not a traditional standalone GUI product.
- The target outcome is to reduce the amount of time users spend managing ledger mechanics while preserving trust and ledger quality.
- The project is a hobby project with no pricing model; distribution is intended to be free and open source.

## Primary User

- Primary user is a solo personal-finance user.
- The user segment to optimize for first is people new to Beancount, not existing expert users.
- These users want the rigor and transparency of Beancount without needing to master every operational detail of ledger maintenance.
- Important adoption driver: low-friction onboarding matters more than advanced power-user flexibility in the first experience.

## Core Problems To Solve

- New users face too much setup complexity before they get value from Beancount.
- Users must manually import statements from inconsistent formats and sources.
- Users repeatedly correct account mappings and categorizations because past decisions are not remembered.
- Ledger edits are risky unless there is a visible safety model, validation, and rollback path.
- Plain-language querying and routine maintenance remain too hard without understanding Beancount internals.
- Users lose efficiency when imports, categorization, pricing, and validation are handled by disconnected tools.

## Product Shape

- The requested form factor is a repo template, similar in spirit to the BMad Method tool, rather than a hosted service.
- The template should bundle agent skills plus the project scaffolding needed for immediate use.
- Setup should be simple enough to feel like installing a small local toolchain.
- User explicitly suggested an install experience similar to `curl http://example.com/install.sh | bash`, meaning minimal friction and quick bootstrap are part of the product promise.
- Product should include Beancount installation and Fava installation as part of the setup story.

## Core Capabilities

- Query the ledger in natural language.
- Edit the ledger directly through the agent workflow.
- Import statements from manual files.
- Auto-categorize transactions.
- Remember prior decisions so repeated work decreases over time.
- Follow Beancount best practices when creating and editing ledgers.
- Keep the product simple to set up and use.

## Import And File Handling

- Initial import scope is manual files, not live bank connectivity.
- Supported file types explicitly requested for V1: PDF, CSV, Excel.
- User noted it could be useful to include or rely on external agent skills specialized for these file types.
- Memory should include prior statement import behavior and the learned flow used to map a statement source into the ledger.
- Product should aim to support a wide variety of statement/account types rather than only retail checking accounts.

## Account And Asset Coverage

- Coverage should include regular day-to-day accounts.
- Coverage should include investing accounts.
- Coverage should include vesting accounts.
- Coverage should include a broad range of assets and expense domains, including daily expenses, savings, investing, vesting, trading, and crypto.
- Product intent is broad personal-finance coverage within a single Beancount-oriented operating model.

## Memory Expectations

- Memory should store preferred account mappings.
- Memory should store merchant-to-category rules.
- Memory should store naming conventions.
- Memory should store recurring corrections.
- Memory should store past statement import mappings and transformation flow.
- Memory is a first-class differentiator, not a minor convenience feature.

## Safety And Trust Model

- Agents are allowed to make edits directly, not only suggest them.
- Every edit or import should be staged in a git branch.
- Beancount validation should run after every edit or import.
- Rollback safeguards are required and should be part of the default workflow.
- Auditability matters because the product deals with financial records and newcomers need confidence before trusting automation.

## Local-First And Privacy Constraints

- Product must be local-first.
- Product must have no cloud dependency.
- Sensitive financial data should remain on the user machine and inside the local repo workflow.
- The product should not depend on hosted SaaS behavior for normal operation.

## External Data

- Product should rely on external sources to find current asset prices.
- Asset price lookup should cover currencies, stocks, and crypto.
- External price data is acceptable even though the product is local-first; the no-cloud requirement is about storage and core operation, not absolute isolation from data sources.

## Differentiation Signals

- Strongest differentiation signal provided by user: agent-first operation through terminal or agent apps like Codex.
- Strongest operational advantage: better memory and better efficiency over time.
- User value proposition should be framed around spending less time managing ledgers.
- The product should be positioned as simpler and more agent-native than current Beancount setup/import workflows.

## Success Signals For V1

- Faster time to first working ledger for a new Beancount user.
- Successful imports from supported file formats with limited manual cleanup.
- Decreasing correction burden over time because the system remembers prior decisions.
- Ability to query the ledger and perform routine edits without deep Beancount expertise.
- Visible trust in the safety model because changes are staged and validated.

## Scope Signals

- In scope for V1: repo template, Beancount and Fava setup, querying, editing, importing, categorization, memory, branch-based safeguards, Beancount validation, broad account/asset support, external asset price lookup.
- Explicitly out of scope for V1: direct bank APIs, mobile app, multi-user collaboration, tax filing, budgeting dashboards, cloud sync.
- User wants broad financial coverage in V1 despite being a newcomer-focused product; PRD should treat this as an ambition that may require careful sequencing.

## Rejected Ideas / Deferred Directions

- Pricing is not a concern; no paid model is needed.
- Cloud-hosted experience is not desired.
- The user is not interested in defining a 2-3 year platform vision right now.
- Direct bank API sync is explicitly deferred from V1.
- Mobile, collaboration, tax, dashboards, and cloud sync are explicitly deferred from V1.

## Open Questions For PRD

- How should the repo template be structured: one orchestrator skill plus specialized sub-skills, or a more modular plugin architecture?
- What exact user journey defines "time to first working ledger" for a newcomer?
- How much human review is required in the import flow, especially for PDF-derived data?
- What external sources should be used for price lookup, and how should trust/fallback behavior work?
- How should memory be stored, versioned, inspected, and corrected by the user?
- How should "broad support for any bank" be translated into realistic V1 acceptance criteria without overpromising universal compatibility?

## Risk Signals Worth Preserving

- V1 scope is broad for a hobby project and may need careful phasing in the PRD.
- PDF import is likely the least structured input path and may be the highest implementation risk.
- Supporting many account and asset classes increases both product value and edge-case complexity.
- Safety and trust are not optional polish; they are part of the core value proposition.
