---
stepsCompleted:
  - "step-01-init"
  - "step-02-discovery"
  - "step-02b-vision"
  - "step-02c-executive-summary"
  - "step-03-success"
  - "step-04-journeys"
  - "step-05-domain"
  - "step-06-innovation"
  - "step-07-project-type"
  - "step-08-scoping"
  - "step-09-functional"
  - "step-10-nonfunctional"
  - "step-11-polish"
  - "step-12-complete"
inputDocuments:
  - "/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/product-brief-auto-bean.md"
  - "/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/product-brief-auto-bean-distillate.md"
documentCounts:
  briefCount: 2
  researchCount: 0
  brainstormingCount: 0
  projectDocsCount: 0
workflowType: 'prd'
classification:
  projectType: "developer_tool"
  domain: "fintech"
  complexity: "high"
  projectContext: "greenfield"
---

# Product Requirements Document - auto-bean

**Author:** chmo
**Date:** 2026-03-29T17:51:00+02:00

## Executive Summary

auto-bean is a local-first, open source developer tool for operating Beancount ledgers through coding agents. It is designed for solo personal-finance users, especially newcomers to Beancount, who want the rigor of plaintext accounting without the ongoing cost of manual setup, importer scripting, repetitive categorization, and risky ledger edits.

The product solves a workflow problem rather than a single feature gap. Users need a fast path from zero to a working ledger, reliable import of real-world financial statements, and confidence that agent-made changes will preserve ledger quality. auto-bean combines repo scaffolding, Beancount and Fava setup, statement import support, learned account and categorization memory, git-backed safety, and validation after every edit or import into one agent-first local workflow.

The intended outcome is that a user can hand the system a statement or account workflow of almost any kind and have the coding agent import it into an existing ledger, or help create a new ledger, with minimal correction required. Over time, the system should reduce manual cleanup further by remembering prior mappings, categorization choices, naming conventions, and import flows.

### What Makes This Special

The product’s differentiator is the operating model. Instead of treating the agent as a thin assistant on top of manual tools, auto-bean treats the coding agent as the primary interface for ledger operations. The user can query the ledger in natural language, perform edits, import statements from PDF, CSV, and Excel, and improve future behavior through supervised corrections.

The core insight is that modern coding agents are capable enough to manage ledger operations directly if they are given the right safety rails and reusable memory. auto-bean combines three properties that alternatives usually separate: minimal setup, local-first privacy, and compounding operational intelligence.

## Project Classification

auto-bean is a developer tool with a strong agent-driven and CLI-style interaction model. It operates in the fintech domain because it manages personal financial ledgers, statement imports, asset valuation context, and financially sensitive records. The project complexity is high because correctness, auditability, trust, edge-case handling, and data integrity are core requirements. This is a greenfield product.

## Success Criteria

### User Success

A new user can install auto-bean, initialize a Beancount repository, create a usable ledger, and import multiple statement accounts in less than one hour. The first session ends with a working ledger, imported data that needs minimal correction, and enough confidence to continue using the workflow.

The key success moment is when the agent can take heterogeneous real-world statements, map them into the ledger with little intervention, and validate the result without requiring deep Beancount expertise. A second success signal is compounding efficiency: repeated imports and categorization work require less manual cleanup over time because prior decisions are remembered and reused.

### Business Success

For V1, business success is personal operational success before broader adoption. The product succeeds if it is reliable enough to use as the primary personal-finance workflow rather than as a side experiment. In the first 3 months, success means it can manage the full personal workflow across setup, import, routine maintenance, and review. In the first 12 months, success means the workflow is stable and reusable enough that it could support other users without depending on one-off fixes.

### Technical Success

The product must not produce invalid ledgers without surfacing that clearly. It must not make silent or unsafe edits that undermine trust in financial records. Setup must be dependable enough that a new user can reach a working baseline without extensive manual debugging. Import workflows must handle PDF, CSV, and Excel inputs robustly enough to be useful in practice, even if some edge cases still require review.

Technical success also requires safety and auditability to be first-class. Every edit or import must run through validation, and changes must be inspectable and reversible through the git-backed workflow.

### Measurable Outcomes

A first-time user can complete setup, create a new ledger, and import multiple statement accounts in under 60 minutes. Imported results are valid Beancount output after the standard validation step. Repeated imports from the same or similar sources require less intervention over time because account mappings, categorization, and import behavior are remembered.

The strongest V1 acceptance criterion is practical self-use: the system is stable and accurate enough to rely on for managing personal finances.

## Product Scope

### MVP - Minimum Viable Product

MVP includes bootstrap setup, Beancount and Fava installation, creation of a new ledger, import support for PDF, CSV, and Excel statements, memory for prior import and categorization decisions, price lookup where needed for valuation context, git-backed safety for edits and imports, post-change Beancount validation, and support for multiple account and asset types linked in one ledger.

### Growth Features (Post-MVP)

Post-MVP work focuses on deeper support for more statement formats and institutions, better handling of complex asset classes and edge cases, stronger memory inspection and correction workflows, more polished onboarding, and improved query and edit ergonomics.

### Vision (Future)

The long-term vision is a local-first standard workflow for agent-operated personal ledger management. In that future state, a user can rely on the agent to set up, import, categorize, maintain, and query a complex multi-account financial life with very little repeated work.

## User Journeys

### Journey 1: Primary User, First Successful Setup and Import

The user starts from a position where Beancount feels powerful but hard to learn, time-consuming, and operationally expensive. Existing alternatives reduce some friction but are often cloud-first, which conflicts with privacy and control goals.

The user installs auto-bean to get a local-first workflow that does not require deep Beancount expertise before first value. In the first session, the user bootstraps the repo, installs the required tooling, creates a new ledger, and hands the agent several statements from different account types.

The critical moment is the first end-to-end import that works with minimal correction: accounts are created correctly, transactions land in the right places, transfers are understood, and the ledger validates. The user leaves the first session with a working personal-finance ledger in under an hour.

### Journey 2: Primary User, Edge Case Recovery During Import

Later, the user works with more realistic data. A new account type appears, transfers between accounts are not detected cleanly, some transactions look duplicated, and one import leaves the ledger unbalanced.

The agent does not silently force a result. It surfaces likely failure points, distinguishes what it knows from what it cannot infer safely, and asks for clarification where needed. The user can inspect the changes, provide targeted guidance, and re-run the process without losing control.

The critical outcome is not just that the import succeeds, but that trust is preserved and the corrected behavior can improve future runs.

### Journey 3: Maintainer-Operator Tuning the System for Personal Use

The same user also acts as maintainer-operator. After repeated use, the user wants the system to fit an actual financial life better by improving repeated categorization patterns, institution-specific import quirks, naming conventions, and other recurring edge cases.

The agent helps inspect and tune memory entries, account mappings, import logic, skill behavior, and repo configuration. The workflow becomes more personalized and more useful over time instead of resetting to a generic baseline.

### Journey 4: Troubleshooting and Trust Recovery After a Bad Import

At the worst moment, something imports incorrectly, the ledger looks wrong, and trust is damaged. The user needs explanation, control, and recovery more than automation.

The agent helps investigate rather than pushing more changes. It shows the diff, highlights suspicious transactions, explains validation failures or inconsistencies, and narrows the problem to a small set of questions. The user can roll back safely or correct the issue with the agent’s help.

### Journey Requirements Summary

These journeys require onboarding that compresses Beancount complexity, import workflows that handle multiple account types and messy data, explicit handling of transfers, duplicates, and unbalanced states, and a trust model built around validation, explanation, and reversibility. They also establish that memory and customization are core capabilities, not optional enhancements.

## Domain-Specific Requirements

### Compliance & Regulatory

There are no formal regulatory or certification requirements for V1 because this is a hobby project rather than a commercial financial product. Even so, the product handles sensitive personal financial records and must adopt practical auditability and privacy standards.

### Technical Constraints

The system must preserve clear git history for all meaningful ledger changes so the user can inspect, compare, and revert work when needed. It must require user approval before creating new structures or making risky edits, especially when the agent is uncertain or a change could materially alter ledger meaning.

### Integration Requirements

V1 does not require formal integrations beyond local statement-file handling and external price lookup where valuation context is needed.

### Risk Mitigations

The main domain risk is erosion of user trust caused by incorrect imports, unsafe edits, or poor explanation of ambiguous results. The product should default to inspectable workflows, validation after edits and imports, explicit approval before risky changes, and recovery paths that make rollback straightforward.

## Innovation & Novel Patterns

### Detected Innovation Areas

The clearest innovation is the operating model: auto-bean treats the coding agent as the primary interface for personal ledger operations rather than as a thin assistant layered on top of existing manual tooling. A second innovation is the combination of local-first privacy, minimal setup, and compounding memory in one system.

### Market Context & Competitive Landscape

The current landscape is fragmented. Traditional Beancount workflows optimize for control and correctness but demand high setup effort and ongoing manual intervention. Paid alternatives reduce operational pain but are often cloud-first, which conflicts with the privacy and ownership goals of users who prefer plaintext accounting.

### Validation Approach

The innovation is validated through real self-use: whether the workflow can reliably set up a ledger, import multiple statement accounts in under an hour, recover from ambiguous or messy imports, and reduce correction effort over repeated use.

### Risk Mitigation

The main innovation risk is that the agent-first model may sound more novel than it is useful. The mitigation is to validate through real usage, keep safety and reversibility mandatory, and measure success by operational outcomes rather than novelty claims.

## Developer Tool Specific Requirements

### Project-Type Overview

auto-bean is a developer tool packaged as a local repo template for agent-operated Beancount workflows. In V1, it is intentionally scoped to a single-user macOS environment and optimized for Codex skills rather than a general-purpose cross-platform interface.

### Technical Architecture Considerations

Codex skills are the primary interaction layer, with scripts used as implementation helpers where appropriate. The stable user-facing surface is therefore a set of skill-driven workflows for setup, import, editing, review, and recovery rather than a public SDK or formal API.

### Language Matrix

V1 does not require multi-language runtime or package ecosystem support. Portability is secondary to making the first supported environment dependable.

### Installation Methods

V1 supports a single primary installation method: one bootstrap script that prepares the environment and initializes the working template.

### API Surface

The main interface surface for V1 is the Codex skill layer. Supporting scripts may exist, but they are implementation details rather than the primary product interface.

### Code Examples

The essential documentation requirement for V1 is a strong quickstart covering bootstrap, ledger initialization, and first meaningful use through Codex.

### Migration Guide

The product should evolve inside an existing repo over time, but formal upgradeability can be deferred from strict MVP scope.

### Implementation Considerations

Implementation should preserve a clean boundary between stable user assets and evolving tool logic. Ledger files, learned memory, and local configuration should be protected from accidental overwrite as the tool evolves.

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

The MVP is a self-use, problem-solving MVP. The goal of Phase 1 is not to impress a broad market. It is to reach a point where the product is genuinely usable for real personal finances with confidence.

### MVP Feature Set (Phase 1)

**Core journeys supported:**
- first-time setup, new ledger creation, and initial multi-account import
- ongoing import of real-world statements into linked accounts
- recovery from ambiguous, duplicated, or unbalanced imports
- trust-preserving review, clarification, and rollback

**Must-have capabilities:**
- bootstrap setup on macOS
- Beancount and Fava installation
- creation of a new ledger
- support for all real account types within one linked ledger
- statement import from PDF, CSV, and Excel
- transfer detection and duplicate handling
- clarification prompts when ambiguity is material
- validation after edits and imports
- git-backed review and rollback
- memory that reduces correction effort over time
- Codex skill-driven workflows as the main interface

Phase 1 succeeds only if all actual accounts can be represented in the ledger and linked together in a way that is trustworthy for real use.

### Post-MVP Features

**Phase 2:**
- stronger polish and reliability across more institutions and statement formats
- better inspection and editing tools for learned memory and mappings
- improved onboarding and troubleshooting documentation
- more robust handling of complex asset classes and edge cases

**Phase 3:**
- formal upgradeable template evolution
- broader environment support beyond one macOS setup
- more reusable packaging and distribution for other users

### Risk Mitigation Strategy

The primary technical risk is whether the full workflow remains trustworthy enough for real finance use. That risk is mitigated through validation at every critical step, explicit approval before risky actions, reversible git-based changes, visible diffs, and conservative clarification behavior when the agent is uncertain.

## Functional Requirements

### Environment Setup & Workspace Initialization

- FR1: A user can bootstrap auto-bean on a supported macOS environment from a single installation entry point.
- FR2: A user can initialize a new auto-bean workspace in a local repository.
- FR3: A user can install and configure required local dependencies needed to operate the ledger workflow.
- FR4: A user can verify that the local environment is ready before attempting ledger operations.
- FR5: A user can access a quickstart workflow that guides the first successful setup and use of the product.

### Ledger Creation & Structure Management

- FR6: A user can create a new Beancount ledger through the agent workflow.
- FR7: A user can define or confirm account structures needed for their personal finance setup.
- FR8: A user can add new accounts to an existing ledger when new institutions or asset types appear.
- FR9: A user can maintain a linked ledger covering all relevant financial accounts.
- FR10: A user can review proposed ledger-structure changes before they are applied.
- FR11: A user can approve or reject risky structural changes proposed by the agent.

### Statement Import & Normalization

- FR12: A user can import financial statements from PDF files into the ledger workflow.
- FR13: A user can import financial statements from CSV files into the ledger workflow.
- FR14: A user can import financial statements from Excel files into the ledger workflow.
- FR15: A user can import data from multiple statement sources into the same ledger.
- FR16: A user can import statements into an existing ledger without recreating the ledger from scratch.
- FR17: A user can use the system to create a new ledger from imported account data when needed.
- FR18: A user can review imported results before accepting them into the ledger.
- FR19: The system can preserve source-to-ledger mapping context across repeated imports from similar sources.

### Transaction Interpretation & Reconciliation

- FR20: A user can have imported transactions mapped into appropriate ledger accounts.
- FR21: A user can have likely transfers between accounts identified during import and review.
- FR22: A user can detect and review potentially duplicated transactions before acceptance.
- FR23: A user can identify unbalanced import outcomes before they are committed.
- FR24: A user can correct ambiguous or incorrect transaction interpretations with agent assistance.
- FR25: A user can clarify how unfamiliar transaction patterns or account behaviors should be handled.
- FR26: A user can preserve corrected interpretations for reuse in future similar imports.

### Memory & Learned Behavior

- FR27: A user can have prior account-mapping decisions reused in future workflows.
- FR28: A user can have prior categorization decisions reused in future workflows.
- FR29: A user can have prior naming conventions reused in future workflows.
- FR30: A user can have prior import-handling decisions reused in future workflows.
- FR31: A user can inspect learned operational memory that affects future behavior.
- FR32: A user can correct or refine learned memory when prior decisions are no longer desired.
- FR33: A user can improve system behavior over time through repeated supervised use rather than one-off scripting.

### Validation, Review & Safe Change Control

- FR34: A user can validate ledger integrity after imports and edits.
- FR35: A user can review meaningful ledger changes before final acceptance.
- FR36: A user can view differences between prior and proposed ledger state.
- FR37: A user can require explicit approval before risky or uncertain changes are applied.
- FR38: A user can have risky actions surfaced distinctly from routine low-risk actions.
- FR39: A user can preserve an auditable history of ledger changes.
- FR40: A user can roll back undesired changes and recover a prior known-good state.

### Pricing & Financial Context

- FR41: A user can retrieve external price data when valuation context is needed.
- FR42: A user can use price data for currencies relevant to the ledger workflow.
- FR43: A user can use price data for equities relevant to the ledger workflow.
- FR44: A user can use price data for crypto assets relevant to the ledger workflow.

### Agent Guidance, Clarification & Troubleshooting

- FR45: A user can interact with the system primarily through Codex skill-driven workflows.
- FR46: A user can receive clarification requests from the agent when available information is insufficient for a trustworthy action.
- FR47: A user can receive explanations of why the agent is uncertain about a proposed interpretation or edit.
- FR48: A user can investigate failed or suspicious imports with agent assistance.
- FR49: A user can inspect validation failures and suspicious ledger changes in a troubleshooting workflow.
- FR50: A user can tune workflow behavior, mappings, and memory over time with agent assistance.

### Documentation & Product Evolution

- FR51: A user can follow a quickstart that covers bootstrap, ledger initialization, and first meaningful use.
- FR52: A user can operate the V1 product without needing a public SDK or formal external API.
- FR53: A user can use the product as an evolving local tool within an existing repository rather than only as a one-time scaffold.

## Non-Functional Requirements

### Performance

The system shall complete import and review of typical statement files fast enough to remain operationally useful in normal personal-finance workflows.

### Security

The system shall keep ledger data and operational context local to the user’s machine by default. It shall not require cloud storage or cloud synchronization for normal operation.

### Reliability

The system shall not silently corrupt ledger state. All meaningful ledger-changing operations shall be validated before acceptance, and failures shall be surfaced clearly to the user. Re-running the same import workflow on the same inputs shall produce deterministic results unless the user intentionally changes configuration, mappings, or memory that affect the outcome.
