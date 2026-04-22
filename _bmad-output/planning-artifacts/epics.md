---
stepsCompleted:
  - "step-01-validate-prerequisites"
  - "step-02-design-epics"
  - "step-03-create-stories"
inputDocuments:
  - "/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/prd.md"
  - "/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/architecture.md"
---

# auto-bean - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for auto-bean, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: A user can bootstrap auto-bean on a supported macOS environment from a single installation entry point.
FR2: A user can initialize a new auto-bean workspace in a local repository.
FR3: A user can install and configure required local dependencies needed to operate the ledger workflow.
FR4: A user can verify that the local environment is ready before attempting ledger operations.
FR5: A user can access a quickstart workflow that guides the first successful setup and use of the product.
FR6: A user can create a new Beancount ledger through the agent workflow.
FR7: A user can define or confirm account structures needed for their personal finance setup.
FR8: A user can add new accounts to an existing ledger when new institutions or asset types appear.
FR9: A user can maintain a linked ledger covering all relevant financial accounts.
FR10: A user can inspect import-derived or agent-made ledger-structure changes through git-backed diffs and workflow summaries after direct mutation, then approve whether the agent should commit and push the result.
FR11: A user can approve or reject risky structural changes proposed by the agent.
FR12: A user can import financial statements from PDF files into the ledger workflow.
FR13: A user can import financial statements from CSV files into the ledger workflow.
FR14: A user can import financial statements from Excel files into the ledger workflow.
FR15: A user can import data from multiple statement sources into the same ledger.
FR16: A user can import statements into an existing ledger without recreating the ledger from scratch.
FR17: A user can use the system to create a new ledger from imported account data when needed.
FR18: A user can inspect imported results, resulting ledger edits, validation outcomes, and a git-backed diff in a direct import workflow before approving commit and push.
FR19: The system can preserve source-to-ledger mapping context across repeated imports from similar sources.
FR20: A user can have imported transactions mapped into appropriate ledger accounts.
FR21: A user can have likely transfers between accounts identified during import and review.
FR22: A user can detect and review potentially duplicated transactions before acceptance.
FR23: A user can identify unbalanced import outcomes before they are committed.
FR24: A user can correct ambiguous or incorrect transaction interpretations with agent assistance.
FR25: A user can clarify how unfamiliar transaction patterns or account behaviors should be handled.
FR26: A user can preserve corrected interpretations for reuse in future similar imports.
FR27: A user can have prior account-mapping decisions reused in future workflows.
FR28: A user can have prior categorization decisions reused in future workflows.
FR29: A user can have prior naming conventions reused in future workflows.
FR30: A user can have prior import-handling decisions reused in future workflows.
FR31: A user can inspect learned operational memory that affects future behavior.
FR32: A user can correct or refine learned memory when prior decisions are no longer desired.
FR33: A user can improve system behavior over time through repeated supervised use rather than one-off scripting.
FR34: A user can validate ledger integrity after imports and edits.
FR35: A user can inspect meaningful ledger changes and their validation outcomes immediately after mutation, approve commit and push only after that inspection, and recover prior known-good state by reverting the commit when needed.
FR36: A user can view differences between prior and resulting ledger state.
FR37: A user can require explicit approval before risky or uncertain changes are committed or pushed.
FR38: A user can have risky actions surfaced distinctly from routine low-risk actions.
FR39: A user can preserve an auditable history of ledger changes.
FR40: A user can roll back undesired changes and recover a prior known-good state.
FR41: A user can retrieve external price data when valuation context is needed.
FR42: A user can use price data for currencies relevant to the ledger workflow.
FR43: A user can use price data for equities relevant to the ledger workflow.
FR44: A user can use price data for crypto assets relevant to the ledger workflow.
FR45: A user can interact with the system primarily through Codex skill-driven workflows.
FR46: A user can receive clarification requests from the agent when available information is insufficient for a trustworthy action.
FR47: A user can receive explanations of why the agent is uncertain about a proposed interpretation or edit.
FR48: A user can investigate failed or suspicious imports with agent assistance.
FR49: A user can inspect validation failures and suspicious ledger changes in a troubleshooting workflow.
FR50: A user can tune workflow behavior, mappings, and memory over time with agent assistance.
FR51: A user can follow a quickstart that covers bootstrap, ledger initialization, and first meaningful use.
FR52: A user can operate the V1 product without needing a public SDK or formal external API.
FR53: A user can use the product as an evolving local tool within an existing repository rather than only as a one-time scaffold.

### NonFunctional Requirements

NFR1: The system shall complete import and review of typical statement files fast enough to remain operationally useful in normal personal-finance workflows.
NFR2: The system shall keep ledger data and operational context local to the user's machine by default.
NFR3: The system shall not require cloud storage or cloud synchronization for normal operation.
NFR4: The system shall not silently corrupt ledger state.
NFR5: All meaningful ledger-changing operations shall be validated before acceptance, and failures shall be surfaced clearly to the user.
NFR6: Re-running the same import workflow on the same inputs shall produce deterministic results unless the user intentionally changes configuration, mappings, or memory that affect the outcome.

### Additional Requirements

- Epic 1 Story 1 should initialize the packaged Python foundation with `uv init --package auto-bean`; the architecture explicitly identifies this as the first implementation story.
- Epic 1 must also make the greenfield quality baseline explicit with CI, deterministic workflow verification, and structured run artifacts before ledger-changing workflows are considered implementation-ready.
- V1 is scoped to local execution on macOS only.
- Beancount and Fava are required local dependencies and should be integrated through infrastructure adapters or scripts.
- Codex skills are the primary user interface; CLI commands and scripts are supporting implementation surfaces rather than the main product interface.
- The canonical source of truth is the user's ledger repository, including Beancount files, configuration files, import artifacts, and governed memory files.
- Operational memory is file-backed in MVP and must be stored in governed, versionable local files behind a memory service abstraction.
- Memory schemas should be versioned and upgradeable without requiring a database migration system in MVP.
- Pydantic v2 models should validate normalized import records, reconciliation candidates, memory records, workflow command inputs and outputs, and mutation plans at service boundaries.
- There is no public API in MVP; internal Python service interfaces and CLI commands should be used instead.
- CLI commands may emit machine-readable JSON for agent orchestration, but that output is an internal automation interface rather than a stable external API.
- Git-backed branching, diffing, review, rollback, and audit history are mandatory workflow infrastructure rather than optional utilities.
- Risky edits and structural changes require user approval before commit/push finalization, with direct mutation results surfaced through validation and git-backed inspection.
- Validation must run after each meaningful ledger-changing action.
- Structured local logging should capture workflow traces, validation outcomes, import decisions, and recovery diagnostics.
- GitHub Actions should provide the CI baseline for lint, typecheck, tests, and deterministic workflow verification.
- Secrets for optional integrations such as price providers should live in local environment configuration or OS-managed secret storage, never in ledger or memory files.
- External price lookup should be isolated behind bounded pricing adapters.
- Persistent cache and database-backed memory are deferred; if needed, only ephemeral in-process caching should be used in MVP.
- Stable user-owned assets must remain clearly separated from evolving tool logic so upgrades do not overwrite ledger, memory, or local configuration data.
- Durable operational memory should live under a governed directory tree such as `.auto-bean/memory/`.
- Review artifacts, diffs, validation reports, and run traces should live under a governed local artifacts area such as `.auto-bean/artifacts/`.
- `ledger.beancount` should remain the stable entrypoint for Fava and validation workflows.
- Only the memory workflow should modify durable memory files under the governed memory tree.
- Readiness checks on an already bootstrapped workspace should complete within 2 minutes on the supported V1 environment, and a typical single-statement import plus review preparation should complete within 3 minutes before approval.
- Every ledger-changing workflow must emit structured diagnostics and an inspectable validation artifact before the result is treated as accepted.

### UX Design Requirements

No UX design document was found in the planning artifacts, and this course correction does not introduce one. Trust-sensitive interaction expectations must therefore remain explicit in story acceptance criteria for quickstart, direct mutation summaries, `git diff` inspection, commit/push approval, rollback, and troubleshooting flows.

### FR Coverage Map

FR1: Epic 1 - bootstrap supported macOS installation
FR2: Epic 1 - initialize local workspace
FR3: Epic 1 - install and configure required dependencies
FR4: Epic 1 - verify environment readiness before ledger operations
FR5: Epic 1 - provide a quickstart workflow for first successful use
FR6: Epic 1 - create a new Beancount ledger through the agent workflow
FR7: Epic 2 - define or confirm account structures principally through first-time statement account import
FR8: Epic 2 - add new accounts to an existing ledger when new institutions or asset types appear through import
FR9: Epic 1 - maintain a linked ledger covering all relevant financial accounts
FR10: Epic 1 - inspect direct structural changes before commit/push finalization
FR11: Epic 1 - approve or reject risky structural changes proposed by the agent
FR12: Epic 2 - import financial statements from PDF files
FR13: Epic 2 - import financial statements from CSV files
FR14: Epic 2 - import financial statements from Excel files
FR15: Epic 2 - import data from multiple statement sources into the same ledger
FR16: Epic 2 - import statements into an existing ledger without recreating the ledger from scratch
FR17: Epic 2 - create a new ledger from imported account data when needed
FR18: Epic 2 - inspect imported results and direct ledger edits before commit/push
FR19: Epic 2 - preserve source-to-ledger mapping context across repeated imports
FR20: Epic 3 - map imported transactions into appropriate ledger accounts
FR21: Epic 3 - identify likely transfers during import and review
FR22: Epic 3 - detect and review potentially duplicated transactions
FR23: Epic 3 - identify unbalanced import outcomes before commit
FR24: Epic 3 - correct ambiguous or incorrect transaction interpretations with agent assistance
FR25: Epic 3 - clarify unfamiliar transaction patterns or account behaviors
FR26: Epic 3 - preserve corrected interpretations for reuse in future similar imports
FR27: Epic 4 - reuse prior account-mapping decisions in future workflows
FR28: Epic 4 - reuse prior categorization decisions in future workflows
FR29: Epic 4 - reuse prior naming conventions in future workflows
FR30: Epic 4 - reuse prior import-handling decisions in future workflows
FR31: Epic 4 - inspect learned operational memory that affects future behavior
FR32: Epic 4 - correct or refine learned memory when prior decisions are no longer desired
FR33: Epic 4 - improve system behavior through repeated supervised use
FR34: Epic 3 - validate ledger integrity after imports and edits
FR35: Epic 3 - inspect meaningful ledger changes after mutation and before commit/push
FR36: Epic 3 - view differences between prior and resulting ledger state
FR37: Epic 3 - require explicit approval before risky or uncertain changes are committed or pushed
FR38: Epic 3 - surface risky actions distinctly from routine low-risk actions
FR39: Epic 3 - preserve an auditable history of ledger changes
FR40: Epic 3 - roll back undesired changes and recover a prior known-good state
FR41: Epic 5 - retrieve external price data when valuation context is needed
FR42: Epic 5 - use price data for currencies relevant to the ledger workflow
FR43: Epic 5 - use price data for equities relevant to the ledger workflow
FR44: Epic 5 - use price data for crypto assets relevant to the ledger workflow
FR45: Epic 1 - interact primarily through Codex skill-driven workflows
FR46: Epic 3 - receive clarification requests when information is insufficient for a trustworthy action
FR47: Epic 3 - receive explanations of agent uncertainty
FR48: Epic 3 - investigate failed or suspicious imports with agent assistance
FR49: Epic 3 - inspect validation failures and suspicious ledger changes in a troubleshooting workflow
FR50: Epic 4 - tune workflow behavior, mappings, and memory over time with agent assistance
FR51: Epic 1 - follow a quickstart covering bootstrap, ledger initialization, and first meaningful use
FR52: Epic 1 - operate V1 without a public SDK or formal external API
FR53: Epic 1 - use the product as an evolving local tool within an existing repository

## Epic List

### Epic 1: Bootstrap a Safe Local Ledger Workspace
Users can install auto-bean, initialize a local workspace, create the base Beancount ledger, and operate through a guided Codex-first workflow with validation, git-backed inspection, and commit/push approval from day one.
**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR9, FR10, FR11, FR45, FR51, FR52, FR53
**Primary NFR support:** NFR4, NFR5, NFR6

### Epic 2: Import Statements and Introduce New Accounts Through Import
Users can import PDF, CSV, and Excel statements into a new or existing ledger, normalize statement data into a reviewable intake result, let the agent write routine import-derived ledger updates directly when confidence is sufficient, inspect the result through validation and git-backed workflow controls, and preserve source-specific context for repeat use.
**FRs covered:** FR7, FR8, FR12, FR13, FR14, FR15, FR16, FR17, FR18, FR19

### Epic 3: Reconcile and Finalize Ledger Changes Safely
Users can turn imported data into trustworthy ledger updates by mapping transactions, handling transfers and duplicates, resolving ambiguity, validating results, inspecting diffs before commit/push, and rolling back when needed.
**FRs covered:** FR20, FR21, FR22, FR23, FR24, FR25, FR26, FR34, FR35, FR36, FR37, FR38, FR39, FR40, FR46, FR47, FR48, FR49

### Epic 4: Learn User Decisions and Improve Over Time
Users can benefit from reusable operational memory, inspect and correct what the system has learned, and tune future workflow behavior through supervised use.
**FRs covered:** FR27, FR28, FR29, FR30, FR31, FR32, FR33, FR50

### Epic 5: Add Valuation Context for Multi-Asset Ledgers
Users can enrich their ledger workflow with external price data for currencies, equities, and crypto without breaking the local-first operating model.
**FRs covered:** FR41, FR42, FR43, FR44

## Epic 1: Bootstrap a Safe Local Ledger Workspace

Users can install auto-bean, initialize a local workspace, create the base Beancount ledger, and operate through a guided Codex-first workflow with validation, git-backed inspection, and commit/push approval from day one.

### Story 1.1: Initialize the packaged auto-bean project foundation

As a solo personal-finance user,
I want the project initialized with the packaged `uv` application foundation,
So that the repo starts from a reproducible, maintainable base that matches the architecture.

**Acceptance Criteria:**

**Given** an empty or pre-bootstrap product repo
**When** the initialization workflow is run
**Then** the project is initialized using `uv init --package auto-bean` or an equivalent resulting packaged structure
**And** the repo contains the expected packaged Python foundation, including `pyproject.toml`, `src/`, and a baseline project entrypoint

**Given** the packaged foundation exists
**When** a developer inspects the repo structure
**Then** stable user-owned assets and evolving tool logic are separated clearly
**And** the structure leaves room for skills, scripts, governed memory, and artifact directories without overwriting ledger assets

### Story 1.2: Bootstrap the auto-bean uv tool on macOS

As a new user on a supported macOS machine,
I want one bootstrap entry point that installs the `auto-bean` uv tool,
So that I can get the product onto my machine before creating a workspace.

**Acceptance Criteria:**

**Given** a supported macOS environment
**When** the user runs `uv tool install --from . --force auto-bean`
**Then** it installs or updates the `auto-bean` uv tool from the product source
**And** it reports any missing prerequisites with clear remediation guidance

**Given** installation has completed
**When** the user verifies the installation
**Then** the system confirms that `uv` is available and that `auto-bean` is discoverable as an installed tool
**And** it returns clear remediation if the shell still cannot find the command

**Given** a user wants to create a working ledger repository
**When** they inspect Story 1.2 outputs
**Then** it is clear that workspace creation belongs to a later `auto-bean init <PROJECT-NAME>` command
**And** Story 1.2 does not create the workspace itself

### Story 1.3: Establish the CI, workflow verification, and diagnostics baseline

As a trust-conscious maintainer-user,
I want the repo to prove basic workflow integrity before ledger-changing automation expands,
So that quality gates are visible and repeatable instead of being implied.

**Acceptance Criteria:**

**Given** the packaged foundation and install workflow exist
**When** the baseline quality workflow is configured
**Then** GitHub Actions runs linting, type validation, automated tests, and deterministic workflow smoke checks for core commands
**And** failures block the baseline from being treated as implementation-ready

**Given** a readiness-significant or ledger-changing workflow is executed
**When** the run completes or fails
**Then** the system emits structured local diagnostics and stores inspectable run artifacts under the governed artifacts area
**And** the artifacts make it possible to review validation, blocked mutations, and troubleshooting context without relying on raw stack traces

### Story 1.4: Create a new base Beancount ledger workspace

As a first-time user,
I want the agent to create a usable base ledger workspace,
So that I can start operating a linked personal-finance ledger without manual file scaffolding.

**Acceptance Criteria:**

**Given** the `auto-bean` tool is installed and the user provides a project name
**When** the `auto-bean init <PROJECT-NAME>` workflow is run
**Then** the system creates a new workspace and the base Beancount ledger entrypoint with the minimum supporting files required for operation
**And** the created workspace is compatible with validation and Fava inspection

**Given** the base ledger workspace has been created
**When** the user reviews the created structure
**Then** the user can inspect what was created before risky structural changes are finalized
**And** the resulting ledger workspace supports later imports into the same linked ledger

### Story 1.5: Inspect and finalize structural ledger changes through the agent workflow

As a trust-conscious user,
I want structural ledger changes summarized and shown through git-backed inspection before they are committed,
So that the agent cannot silently finalize changes that alter the meaning of my ledger.

**Acceptance Criteria:**

**Given** a direct structural change to the ledger or workspace
**When** the workflow finishes mutating and validating the result
**Then** the system presents a concise summary plus `git diff` before commit/push finalization
**And** the user can explicitly approve or reject the commit/push step

**Given** a structural change is approved for commit/push
**When** the workflow completes
**Then** the resulting change is captured in inspectable history with diff visibility
**And** the system preserves an auditable trail for later revert-based rollback

### Story 1.6: Deliver the Codex-first quickstart for first meaningful use

As a new user,
I want a quickstart workflow that shows how to bootstrap, initialize a ledger, and reach first value,
So that I can become operational in the first session without needing a public SDK or external API.

**Acceptance Criteria:**

**Given** a new user opening the repo for the first time
**When** they follow the quickstart guidance
**Then** they can install the tool, initialize the workspace, create the base ledger, and understand the next import-oriented workflow
**And** the guidance uses Codex skill-driven interaction as the primary interface

**Given** the quickstart documentation is available
**When** a user follows it end to end
**Then** the documented path does not depend on a public SDK or formal external API
**And** it positions the product as an evolving local tool within the repository

## Epic 2: Import Statements and Introduce New Accounts Through Import

Users can import PDF, CSV, and Excel statements into a new or existing ledger, normalize statement data into a reviewable intake result, let the agent write routine import-derived ledger updates directly when confidence is sufficient, inspect the result through validation and git-backed workflow controls, and preserve source-specific context for repeat use.

### Story 2.1: Import statement files into a normalized intake workflow

As a user managing real financial records,
I want PDF, CSV, and Excel statements ingested into one normalized intake workflow,
So that different statement formats can enter the ledger pipeline consistently.

**Acceptance Criteria:**

**Given** a supported statement file in PDF, CSV, or Excel format
**When** the import workflow is run
**Then** the system parses the file into a normalized intermediate representation suitable for downstream review and reconciliation
**And** the workflow reports format-specific parsing failures clearly without mutating the ledger
**And** the run records a structured import artifact that keeps the source, parse status, and blocking issues inspectable for troubleshooting

**Given** multiple supported statement files from different sources
**When** the user imports them into the same ledger workflow
**Then** each file is normalized through the same intake contract
**And** the resulting import runs remain distinguishable by source and input artifact

### Story 2.2: Create or extend a ledger from first-time imported account statements

As a first-time or expanding ledger user,
I want the agent to create or extend the ledger directly from first-time imported account statements when the evidence is sufficient,
So that account creation happens principally from real imported account evidence rather than separate manual setup.

**Acceptance Criteria:**

**Given** a statement from an account not yet represented in the ledger
**When** the import workflow analyzes the source
**Then** the system writes the new account structure needed for that imported account directly into the ledger as part of the import workflow
**And** the workflow makes clear that the account was first-seen and import-derived

**Given** the user is starting from no existing ledger or from an incomplete ledger
**When** imported account data provides enough information to proceed
**Then** the system can create a new ledger baseline or extend the existing ledger from that imported account data
**And** standalone account creation is not required for the normal first-seen account path
**And** the workflow shows the resulting diff and asks whether the agent should commit and push the validated change

### Story 2.3: Review normalized import results before finalizing direct ledger edits

As a trust-conscious user,
I want to review normalized import results, direct ledger edits, and validation outcomes in one import workflow,
So that I stay in control of what enters my ledger before the agent commits and pushes the result.

**Acceptance Criteria:**

**Given** a completed import run with normalized statement records and direct ledger edits derived from them
**When** the system presents the import result
**Then** the user can review the normalized intake result, validation outcome, and resulting diff before commit/push
**And** the review surface distinguishes parsed transaction records from the ledger changes derived from them
**And** the workflow makes clear that commit/push remains the final approval boundary

**Given** an import result contains issues, uncertainty, low-confidence inferences, or failed validation
**When** the user reviews the result
**Then** the workflow surfaces those concerns clearly before commit/push proceeds
**And** the user can reject or defer finalization without corrupting existing ledger state

### Story 2.4: Persist source-specific import context for repeated imports

As a repeat user,
I want source-specific import context to be remembered,
So that repeated imports from the same or similar sources require less setup over time.

**Acceptance Criteria:**

**Given** a completed import from a recognized source or statement pattern
**When** the import workflow is finalized
**Then** the system persists source-to-ledger import context needed to improve later runs
**And** that context is stored in a governed local form consistent with the architecture

**Given** a later import from the same or similar source
**When** the import workflow starts
**Then** the system can reuse relevant prior source context to reduce repetitive setup or mapping work
**And** reused context remains reviewable rather than silently forcing an outcome

## Epic 3: Reconcile and Finalize Ledger Changes Safely

Users can turn imported data into trustworthy ledger updates by mapping transactions, handling transfers and duplicates, resolving ambiguity, validating results, reviewing diffs, and rolling back when needed.

### Story 3.1: Transform normalized import results into direct ledger postings with commit-gated acceptance

As a user importing real financial activity,
I want normalized imported transactions transformed into direct ledger postings,
So that reviewed statement data can be turned into validated accounting changes that I can inspect before commit/push.

**Acceptance Criteria:**

**Given** normalized imported transactions that have passed the Epic 2 import review and an existing ledger context
**When** the reconciliation workflow runs
**Then** the system transforms the imported transactions into ledger postings mapped to appropriate ledger accounts
**And** the resulting change is summarized and shown through git-backed diff before commit/push

**Given** imported transactions include patterns seen before
**When** the mapping workflow evaluates them
**Then** relevant prior mappings may be reused to improve the resulting postings
**And** reused mappings remain attributable and reviewable

### Story 3.2: Detect transfers, duplicates, and unbalanced outcomes during reconciliation

As a user reviewing imported ledger changes,
I want likely transfers, duplicates, and unbalanced outcomes flagged,
So that common financial-import errors are caught before acceptance.

**Acceptance Criteria:**

**Given** candidate transactions from one or more imports
**When** the reconciliation checks run
**Then** the system identifies likely inter-account transfers, potential duplicate transactions, and unbalanced proposed outcomes
**And** each issue type is surfaced distinctly for review

**Given** the workflow detects no safe resolution for a flagged issue
**When** the review result is presented
**Then** the unresolved issue is preserved as an explicit warning or blocker
**And** the system does not silently force a misleading ledger result

### Story 3.3: Run clarification workflows for ambiguous or unfamiliar transaction patterns

As a user facing ambiguous import results,
I want the agent to ask targeted clarification questions and explain uncertainty,
So that I can correct the result without losing trust in the workflow.

**Acceptance Criteria:**

**Given** imported transactions contain ambiguity, unfamiliar patterns, or low-confidence interpretations
**When** the reconciliation workflow cannot proceed safely
**Then** the agent requests clarification before applying a risky interpretation
**And** it explains why it is uncertain in terms the user can act on

**Given** the user provides clarification
**When** the workflow resumes
**Then** the system applies the clarification to the current reconciliation result
**And** the corrected interpretation can later be reused through the governed memory path


### Story 3.4: Troubleshoot suspicious or failed imports with guided diagnostics

As a user recovering from a bad import or failed validation,
I want guided troubleshooting support,
So that I can understand the failure and correct it safely.

**Acceptance Criteria:**

**Given** an import result is suspicious, failed, or blocked by validation
**When** the troubleshooting workflow is run
**Then** the system presents the relevant validation failures, suspicious changes, or reconciliation warnings in one guided diagnostic view
**And** the workflow narrows the problem to actionable issues rather than pushing further unsafe changes
**And** the guided view is derived from structured diagnostics and saved run artifacts rather than ad hoc reconstruction

**Given** the user is investigating a failed or suspicious result
**When** the agent explains the issue
**Then** the explanation distinguishes confirmed problems from inferred possibilities
**And** it helps the user decide whether to clarify, retry, reject, or roll back

## Epic 4: Learn User Decisions and Improve Over Time

Users can benefit from reusable operational memory, inspect and correct what the system has learned, and tune future workflow behavior through supervised use.

### Story 4.1: Persist governed memory for mappings, categorization, naming, transfer detection, deduplication and import behavior

As a repeat user,
I want the system to persist learned operational decisions in governed local memory,
So that useful past decisions can improve future workflows without becoming opaque or unsafe.

**Acceptance Criteria:**

**Given** a workflow produces reusable decisions such as account mappings, categorization outcomes, naming conventions, transfer detection logic, deduplication or import-handling rules
**When** the workflow finalizes an approved result
**Then** the system persists those decisions through the governed memory abstraction
**And** the stored memory remains local, versionable, and separate from raw ledger files

**Given** memory is persisted for MVP
**When** the underlying storage is inspected
**Then** the memory is file-backed in a governed local structure consistent with the architecture
**And** the storage contract allows future migration without changing higher-level workflow behavior

### Story 4.2: Reuse learned memory in future import and reconciliation workflows

As a repeat user,
I want prior decisions reused in later workflows,
So that repeated imports and categorizations require less manual correction.

**Acceptance Criteria:**

**Given** relevant governed memory exists from prior approved workflows
**When** a new import or reconciliation run begins
**Then** the system can reuse applicable prior mappings, categorizations, naming conventions, or import behaviors
**And** reused memory reduces repetitive setup or correction work

**Given** reused memory affects a current proposal
**When** the proposal is presented for review
**Then** the memory influence is attributable and reviewable
**And** the system does not silently conceal that past decisions shaped the outcome

### Story 4.3: Inspect stored memory that influences future behavior

As a user maintaining trust in the system,
I want to inspect learned memory entries,
So that I can understand what prior decisions may affect future results.

**Acceptance Criteria:**

**Given** governed memory has been accumulated over prior workflows
**When** the user runs the memory inspection workflow
**Then** the system presents the stored memory entries in a reviewable form
**And** entries are understandable enough for the user to see what decision or pattern each one represents

**Given** a memory entry is being inspected
**When** the user reviews its details
**Then** they can identify the type of learned behavior involved, such as mapping, categorization, naming, or import handling
**And** they can see enough context to decide whether the memory should remain in effect

### Story 4.4: Correct or refine learned memory through an explicit workflow

As a user whose past decisions may no longer be desired,
I want to correct or refine learned memory explicitly,
So that future behavior improves instead of repeating outdated assumptions.

**Acceptance Criteria:**

**Given** an existing memory entry is wrong, outdated, or too broad
**When** the user invokes the memory correction workflow
**Then** the system allows that memory to be corrected, refined, or removed through an explicit governed path
**And** the change is treated as a controlled update rather than an opaque side effect

**Given** a memory correction has been made
**When** a later workflow relies on the affected memory type
**Then** the corrected memory influences future proposals instead of the superseded behavior
**And** the user can inspect that the update took effect

### Story 4.5: Tune workflow behavior over time through supervised feedback

As a long-term user,
I want my repeated corrections and feedback to improve the workflow over time,
So that the system becomes more personalized and efficient through supervised use.

**Acceptance Criteria:**

**Given** the user provides repeated corrections or confirmations across imports and reconciliations
**When** those workflows are completed over time
**Then** the system improves future proposals using approved supervised feedback
**And** the improvement occurs through governed memory or configuration rather than hidden prompt drift

**Given** workflow behavior has adapted over time
**When** the user evaluates a later run
**Then** the user can still inspect, challenge, or refine the decisions influencing that run
**And** personalization does not remove reviewability or user control

## Epic 5: Add Valuation Context for Multi-Asset Ledgers

Users can enrich their ledger workflow with external price data for currencies, equities, and crypto without breaking the local-first operating model.

### Story 5.1: Retrieve external price data through bounded pricing adapters

As a user maintaining a multi-asset ledger,
I want the system to retrieve external price data through bounded integrations,
So that valuation context can be added without turning the product into a cloud-dependent workflow.

**Acceptance Criteria:**

**Given** a workflow needs valuation context for a supported asset
**When** the pricing workflow is run
**Then** the system retrieves external price data through a dedicated pricing adapter
**And** the integration remains bounded so core ledger data and workflow state stay local

**Given** the pricing adapter is configured for MVP use
**When** a developer inspects the implementation boundary
**Then** the pricing integration is isolated from core ledger and memory logic
**And** provider-specific behavior does not leak into unrelated workflow layers

### Story 5.2: Apply currency, equity, and crypto valuation context in ledger workflows

As a user with multiple asset types,
I want valuation context available for currencies, equities, and crypto,
So that the ledger workflow can support the asset classes I actually use.

**Acceptance Criteria:**

**Given** a workflow requires price data for a supported currency, equity, or crypto asset
**When** the valuation step runs
**Then** the system can retrieve and apply the relevant price context for that asset class
**And** the result is represented in a form usable by downstream ledger workflows

**Given** multiple supported asset classes appear in the same broader ledger workflow
**When** valuation context is requested
**Then** the system handles each supported asset type through a consistent pricing interface
**And** support for one asset class does not require a separate user-facing workflow model

### Story 5.3: Handle pricing failures and gaps without breaking local-first safety

As a trust-conscious user,
I want pricing failures or missing data handled safely,
So that an external lookup problem does not silently damage my ledger workflow.

**Acceptance Criteria:**

**Given** a pricing lookup fails, times out, or returns incomplete data
**When** the valuation workflow completes
**Then** the system surfaces the failure or gap clearly to the user
**And** it does not misrepresent missing valuation data as a successful resolved result

**Given** a broader workflow can continue without valuation data
**When** pricing data is unavailable
**Then** the system preserves local-first control and allows the user to decide how to proceed
**And** the failure remains inspectable for later retry or troubleshooting
