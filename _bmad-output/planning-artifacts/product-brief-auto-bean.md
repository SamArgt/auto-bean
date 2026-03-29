---
title: "Product Brief: auto-bean"
status: "complete"
created: "2026-03-29T14:14:03Z"
updated: "2026-03-29T14:15:41Z"
inputs: []
---

# Product Brief: auto-bean

## Executive Summary

Managing a personal Beancount ledger is powerful, but the day-to-day workflow is still too manual for most people, especially newcomers. Users have to learn Beancount conventions, install and wire together tools, import statements from inconsistent file formats, clean up transactions, choose accounts, categorize entries, and validate that nothing broke. The result is a finance workflow that is accurate in theory but costly in time, attention, and confidence.

auto-bean is a local-first, open source repo template that gives coding agents like Codex a complete set of skills for operating a Beancount ledger safely and efficiently. It packages Beancount and Fava installation, agent-first terminal and app workflows, git-backed change safety, statement import support for PDF, CSV, and Excel, memory for past categorization and import decisions, and validation after every edit or import. The product is designed so a solo user can spend less time managing ledger mechanics and more time understanding their finances.

For the first version, auto-bean focuses on the highest-friction workflow: helping new Beancount users get set up quickly, import real-world financial statements, maintain a clean ledger across cash, savings, investments, vesting, trading, and crypto assets, and trust that agent-made changes are auditable and reversible.

## The Problem

Beancount attracts users who want precision, transparency, and full ownership of their financial records. But the practical workflow is still fragmented. New users must learn Beancount structure and best practices while also solving import problems, transaction categorization, account mapping, price lookup, and ledger validation. Each new account type or statement format introduces more manual work.

Today, users often patch together scripts, importer rules, spreadsheets, and repetitive edits. This creates several persistent pain points:

- Setup is too heavy for newcomers who want results quickly.
- Statement imports are inconsistent across banks, brokerages, vesting platforms, and crypto services.
- Categorization and account mapping require repetitive manual corrections.
- Users cannot rely on persistent memory of prior import and ledger decisions.
- Ledger edits feel risky because mistakes can silently degrade data quality.
- Answering simple finance questions still requires understanding Beancount internals or writing ad hoc queries.

The cost of the status quo is not just time. It is also trust. If users do not trust imports, categorizations, or edits, they fall back to manual bookkeeping and lose the efficiency benefits that agent-assisted finance should provide.

## The Solution

auto-bean is an agent-first Beancount operations template. A user installs a small local toolchain, initializes a repository, and gains a set of skills that let an agent query the ledger, import statements, propose or apply edits, remember prior choices, and validate the ledger after every change.

The core experience centers on safe, local automation:

- Query ledgers in natural language through a terminal or agent app such as Codex.
- Import manual statement files from PDF, CSV, and Excel into an existing ledger workflow.
- Learn recurring account mappings, merchant categorizations, naming conventions, and prior import flows.
- Support a broad range of account and asset types, including day-to-day spending, savings, investing, vesting, trading, and crypto.
- Fetch current prices for currencies, equities, and crypto assets from external sources when valuation context is needed.
- Stage changes in git branches so every edit is auditable, reviewable, and reversible.
- Run Beancount validation after every edit or import to preserve ledger integrity.

The outcome is not just automation. It is a safer operating model for personal finance ledgers that makes Beancount accessible to people who would otherwise bounce off the setup and maintenance burden.

## What Makes This Different

auto-bean is differentiated by its combination of agent-first interaction, local-first trust, and memory-driven efficiency.

- Agent-first from day one: the primary interface is the coding agent, not a collection of scripts the user must learn.
- Built for newcomers: the product starts with setup simplicity and guided operations rather than assuming Beancount expertise.
- Memory as a core feature: prior import behavior, account choices, and categorization corrections become reusable operational knowledge.
- Safety by default: git branching plus post-change Beancount validation creates a clear guardrail model for autonomous edits.
- Broad financial coverage: the initial design aims to support common personal-finance realities, including banking, investing, vesting, and crypto workflows in one system.
- Local-first and no-cloud: sensitive financial data remains on the user's machine and inside their repository.

This is not a hosted finance product, a budgeting app, or a dashboard-first experience. Its advantage is practical execution: helping users maintain trustworthy ledgers with less effort and less repeated work.

## Who This Serves

The primary user is a solo personal-finance user who wants the rigor of Beancount but does not want to become an expert in every operational detail required to keep a ledger accurate and current.

These users want:

- A faster path from installation to a working ledger
- Help importing messy real-world statements
- Reliable categorization and account assignment over time
- Confidence that changes made by an agent can be inspected and rolled back
- A local, private workflow without cloud dependency

Their success looks like spending less time on ledger maintenance and more time using the ledger to understand spending, savings, investments, and net worth.

## Success Criteria

The first version of auto-bean succeeds if it measurably reduces the time and effort required to operate a personal Beancount ledger while preserving user trust.

Key success signals:

- Time to first working ledger is dramatically shorter for a new Beancount user.
- Users can complete statement imports from supported file types with a high success rate.
- Manual correction work drops over time because the system remembers prior decisions.
- Users can query their ledger and make routine edits without diving into Beancount internals.
- Every edit or import passes Beancount validation before being accepted.
- Users trust the git-backed safety model and can inspect or revert agent-made changes when needed.

## Scope

### In Scope for V1

- Open source repo template distribution
- Local installation of Beancount and Fava
- Agent skills for querying, editing, importing, categorizing, and remembering
- Support for manual imports from PDF, CSV, and Excel
- Git branch staging and rollback safeguards
- Beancount validation after every edit and import
- Support for diverse account and asset classes across spending, savings, investing, vesting, trading, and crypto
- External price lookup for currencies, stocks, and crypto assets

### Explicitly Out of Scope for V1

- Direct bank API synchronization
- Mobile applications
- Multi-user collaboration
- Tax filing workflows
- Budgeting dashboards
- Cloud synchronization or hosted services

## Vision

In the near term, auto-bean aims to become the simplest trustworthy way for an individual to run a Beancount ledger with agent assistance. The emphasis is not on becoming a broad finance platform immediately, but on making ledger operations dramatically easier, safer, and more repeatable for real personal-finance workflows.

If auto-bean succeeds at that, it will establish a practical standard for how coding agents can manage financial ledgers responsibly: local-first, auditable, memory-enabled, and grounded in Beancount best practices.
