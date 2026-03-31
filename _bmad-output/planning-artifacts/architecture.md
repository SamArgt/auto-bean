---
stepsCompleted:
  - 1
  - 2
  - 3
  - 4
  - 5
  - 6
  - 7
inputDocuments:
  - "/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/prd.md"
  - "/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/product-brief-auto-bean.md"
  - "/Users/sam/Projects/auto-bean/_bmad-output/planning-artifacts/product-brief-auto-bean-distillate.md"
workflowType: 'architecture'
project_name: 'auto-bean'
user_name: 'chmo'
date: '2026-03-29T17:04:54+02:00'
lastStep: 8
status: 'complete'
completedAt: '2026-03-29T17:04:54+02:00'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
The PRD defines 53 functional requirements across the full lifecycle of a local-first, agent-operated Beancount system. Architecturally, they cluster into nine capability areas.

Environment and setup requirements establish a bootstrap path for a supported macOS environment, local dependency installation, workspace initialization, readiness verification, and quickstart guidance. These imply a setup/orchestration layer with environment checks, install tasks, and repeatable initialization flows.

Ledger creation and structure management requirements establish that the system must create new ledgers, extend existing ledgers, propose structural changes, and require approval before risky structural edits. This implies a ledger-structure service with explicit review and authorization boundaries rather than unconstrained agent mutation.

Statement import and normalization requirements define a multi-format ingestion pipeline for PDF, CSV, and Excel sources, with support for both importing into existing ledgers and generating starting structure from imported data. This implies format-specific ingestion adapters feeding a normalized transaction model before ledger posting decisions are made.

Transaction interpretation and reconciliation requirements establish account mapping, transfer detection, duplicate detection, unbalanced-state identification, clarification loops, and reuse of corrected interpretations. Architecturally, this is a decisioning and reconciliation layer that must operate conservatively and surface uncertainty explicitly.

Memory requirements establish that prior account mappings, categorizations, naming conventions, and import behaviors must be persisted, inspected, corrected, and improved over time. This implies a governed operational-memory subsystem with versioned, reviewable, user-correctable state rather than opaque prompt memory.

Validation, review, and safe change control requirements define post-change validation, meaningful review, diff visibility, approval gating, audit history, and rollback. These requirements strongly imply a safety-control layer around all ledger-changing operations, likely backed by git and Beancount validation as mandatory gates.

Pricing and financial context requirements define external valuation lookups for currencies, equities, and crypto. This implies isolated market-data adapters that can enrich workflows without breaking the product's local-first operating model.

Agent guidance, clarification, and troubleshooting requirements define Codex skills as the primary interface, with explanation and troubleshooting workflows when ambiguity or failures occur. This implies an orchestration layer that manages user interaction, confidence thresholds, and recovery paths.

Documentation and product-evolution requirements establish quickstart-driven onboarding and an evolving local tool model rather than a public SDK. The architecture therefore needs a stable user-facing workflow while allowing internal scripts, prompts, and rules to evolve safely.

**Non-Functional Requirements:**
The most important NFR is trust-preserving reliability. The system must not silently corrupt ledger state, and every meaningful ledger change must be validated before acceptance. Deterministic reruns are also required unless the user intentionally changes governing memory or configuration.

Security and privacy requirements are local-first by default. Ledger data and operational context must remain on the user's machine, and the architecture should avoid hosted dependencies for core workflows. External price data is allowed, but only as a bounded integration.

Performance requirements are pragmatic rather than benchmark-driven: import and review of normal statement files must be fast enough to remain operationally useful. This suggests the architecture should optimize for interactive workflows, bounded batch operations, and efficient review cycles rather than large-scale distributed processing.

**Scale & Complexity:**
This project is high complexity despite being single-user and local-first. Complexity comes from correctness, ambiguity handling, financial edge cases, and the requirement to preserve user trust under imperfect inputs.

- Primary domain: local-first agent-driven fintech workflow automation
- Complexity level: high
- Estimated architectural components: 7-9 major subsystems

The most likely major subsystems are:
1. agent workflow orchestration
2. environment/bootstrap management
3. import adapters and normalization
4. reconciliation and interpretation engine
5. ledger mutation and structure management
6. validation/review/safety controls
7. operational memory and configuration
8. market data integration
9. troubleshooting and observability support

### Technical Constraints & Dependencies

Known constraints and dependencies from the PRD and briefs include:
- macOS is the only intended supported environment for V1
- Codex skills are the primary user interface
- Beancount and Fava are required local dependencies
- git-backed branching, diffing, and rollback are core workflow dependencies
- statement ingestion must support PDF, CSV, and Excel inputs
- external price data sources are needed for currencies, equities, and crypto
- the system must preserve a clean separation between stable user-owned assets and evolving tool logic
- risky edits and structural changes require explicit user approval
- deterministic behavior is expected for repeated imports unless memory or config changes

### Cross-Cutting Concerns Identified

Several concerns affect nearly every subsystem.

Validation is universal: imports, edits, structure changes, and recovery flows all depend on ledger integrity checks before acceptance.

Auditability is universal: users must be able to inspect diffs, understand changes, and recover prior good states through git-backed history.

Uncertainty management is universal: the agent must distinguish between confident automation and ambiguous interpretation, escalating to clarification instead of forcing unsafe outcomes.

Memory governance is universal: learned behavior improves efficiency, but must remain inspectable, correctable, and bounded so that historical decisions do not silently degrade future imports.

Privacy is universal: architecture must keep primary data local and avoid unnecessary remote dependencies.

Consistency of agent behavior is universal: because the product is agent-first, architecture must define clear boundaries, contracts, and review gates so different skills or future agent runs do not mutate the ledger inconsistently.

Delivery integrity is universal: because trust in V1 depends on agent workflows behaving predictably, CI verification, deterministic smoke checks, and structured diagnostics are part of the runtime trust model rather than optional engineering polish.

## Starter Template Evaluation

### Primary Technology Domain

CLI / local automation tool with Python packaging requirements, based on project requirements analysis.

The key reasons are:
- the product is agent-first and repo-local, not a web UI or hosted app
- Beancount and Fava are Python-native dependencies
- the core surface is a command-driven workflow with supporting scripts and skills
- V1 is macOS-local and single-user, so operational simplicity matters more than polyglot flexibility

### Starter Options Considered

**Option 1: `uv` packaged application starter**
This is the strongest fit. Official `uv` docs currently distinguish between default application projects and packaged applications, with `uv init --package` creating a `src`-based packaged layout suitable for CLIs, tests, and future distribution.

Architectural implications:
- modern `pyproject.toml` project foundation
- `src/` layout by default for cleaner packaging boundaries
- lockfile and environment management integrated through `uv`
- simple path to adding Typer, pytest, and Ruff as explicit first-story decisions
- good fit for a local-first tool where bootstrap simplicity is part of the product promise

**Option 2: `Hatch` project starter**
Still viable and maintained. `hatch new` creates a `src` plus `tests` layout and gives a conventional Python packaging baseline.

Architectural implications:
- strong packaging defaults
- conventional structure
- more opinionated around Hatch as the project manager
- weaker fit than `uv` for this project because the product already values minimal bootstrap and `uv` aligns better with that operational model

**Option 3: `Copier` as the initial project generator**
Useful, but at the wrong layer for the first runtime foundation. Copier is best used later to generate or evolve the user-facing repo template once the internal project structure is stable.

Architectural implications:
- strong future fit for turning auto-bean into a reusable template
- not sufficient alone as the main runtime/project-management foundation
- should sit above the chosen Python project starter, not replace it

### Selected Starter: `uv` Packaged Application

**Rationale for Selection:**
`uv` is the best match for the project's local-first, bootstrap-light, Python-native architecture. It gives a minimal but modern packaged-app foundation without overcommitting the project to a large framework. It also matches the product promise of quick setup and clean dependency management better than heavier starters.

This choice keeps the architecture clear:
- `uv` provides project/runtime/package management
- Typer can provide the CLI command surface
- project-specific skills and scripts remain first-class instead of being buried in framework conventions
- Copier can later wrap this structure into the end-user repo template

**Initialization Command:**

```bash
uv init --package auto-bean
```

**Architectural Decisions Provided by Starter:**

**Language & Runtime:**
Python packaged application using a modern `pyproject.toml` workflow. This aligns with the Beancount and Fava ecosystem and keeps the implementation language close to core dependencies.

**Styling Solution:**
Not applicable at starter level. This starter does not introduce frontend concerns, which is appropriate because V1 is not a web-first product.

**Build Tooling:**
`uv` establishes dependency management, project metadata, environment management, and lockfile-driven reproducibility. This is a strong foundation for deterministic local workflows.

**Testing Framework:**
Not included by default in the starter. This is actually desirable here, because we should make test strategy an explicit architecture decision instead of inheriting unnecessary defaults. The expected follow-on is `pytest`.

**Code Organization:**
Packaged `src/` layout, which provides a clean separation between importable application code and repo-level scripts, docs, and generated artifacts.

**Development Experience:**
Fast project bootstrap, simple dependency installation, lockfile support, and a low-friction local workflow. This supports the product requirement that setup feel lightweight and dependable.

**Note:** Project initialization using this command should be the first implementation story.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Source of truth: Beancount ledger files and repo-managed artifacts remain the canonical data model
- Operational memory: file-only memory for MVP, stored locally in versionable project-controlled files
- Security model: single-user local execution with no application-level authentication
- API boundary: no public API in MVP; use internal Python service interfaces and CLI commands only
- Validation model: typed validation at service boundaries with Pydantic v2
- CI baseline: GitHub Actions for lint, typecheck, tests, and deterministic workflow verification

**Important Decisions (Shape Architecture):**
- Keep memory storage abstracted behind a repository/service boundary so file-backed MVP storage can later move to PostgreSQL plus vector retrieval without rewriting workflow logic
- Treat git review, diffing, and rollback as mandatory workflow infrastructure rather than optional utilities
- Use machine-readable command outputs where needed for agent orchestration, but do not expose them as a stable external API
- Prefer structured logs and explicit result objects over implicit script output

**Deferred Decisions (Post-MVP):**
- PostgreSQL and vector search for RAG-backed memory retrieval
- Multi-user authn/authz
- Remote execution model
- Public API surface
- Distributed caching or background worker architecture

### Data Architecture

**Canonical Data Model:**
The canonical source of truth is the user's ledger repository: Beancount files, configuration files, import artifacts, and governed memory files. This matches the local-first trust model and keeps all meaningful financial state inspectable in ordinary files.

**Operational Memory Strategy:**
Operational memory will be file-only in MVP. This should cover:
- account mapping rules
- merchant/category mappings
- naming conventions
- import-source handling patterns
- reusable clarification outcomes

The memory layer should be designed behind an internal abstraction so implementation code depends on a memory service contract, not directly on flat files. That preserves a clean migration path to PostgreSQL plus vector retrieval in V2 if memory volume, semantic lookup, or ranking quality outgrow file-based retrieval.

**Data Validation Strategy:**
Use Pydantic v2 models for typed validation at system boundaries:
- normalized import records
- reconciliation candidates
- memory records
- workflow command inputs/outputs
- proposed ledger mutation plans

This reduces agent inconsistency by forcing structured intermediate representations instead of ad hoc dictionaries and text blobs.

**Migration Approach:**
No database migration system is needed in MVP because memory is file-backed. Instead, define versioned schemas for memory documents and include lightweight upgrade transforms when formats evolve.

**Caching Strategy:**
No dedicated cache layer in MVP. If needed, use ephemeral in-process caching only for bounded tasks such as repeated price lookups or repeated parsing during a single workflow run. Persistent cache should be deferred until real bottlenecks appear.

### Authentication & Security

**Authentication Method:**
No application-level authentication in MVP.

**Authorization Pattern:**
The trust boundary is the local machine user plus explicit in-workflow approval gates. Risky actions require deliberate user approval before ledger mutation.

**Secrets Handling:**
Secrets for optional integrations such as price data providers should live in local environment configuration or OS-managed secret storage, never in the ledger or operational memory files.

**Data Protection Approach:**
Protect privacy by keeping all primary financial data local, minimizing outbound calls, and isolating remote integrations behind narrow adapters.

**Security Posture:**
Security in MVP is primarily about preventing unsafe actions, silent corruption, and accidental disclosure, not multi-user access control. The most important controls are:
- approval before risky changes
- validation after each change
- visible diffs
- reversible history
- bounded handling of external data access

### API & Communication Patterns

**External API Strategy:**
No public REST or GraphQL API in MVP.

**Internal Communication Pattern:**
Use internal Python service boundaries with typed request/response models. CLI commands and agent skills should call application services, not manipulate ledger files directly.

**Error Handling Standard:**
Use structured domain errors with user-safe explanations and machine-readable failure categories. Distinguish clearly between:
- validation failure
- ambiguous interpretation
- external dependency failure
- unsafe proposed mutation
- recoverable workflow interruption

**Automation Interface:**
Where automation requires structured output, CLI commands may emit JSON, but this is an internal automation interface rather than a supported public API contract.

**Rate Limiting Strategy:**
Not applicable for MVP because there is no network-facing API. External adapters may impose their own provider-aware throttling where needed.

### Frontend Architecture

No dedicated frontend architecture is required for MVP.

The primary user interface is:
- Codex skills
- terminal/CLI workflows
- existing local tools such as Fava for ledger inspection where appropriate

This keeps implementation focused on workflow orchestration, data integrity, and reviewability rather than introducing a new UI surface prematurely.

### Infrastructure & Deployment

**Execution Model:**
Local execution on macOS for MVP.

**CI/CD Approach:**
Use GitHub Actions for repository validation:
- Ruff lint/format checks
- pytest test suite
- type validation for core modules
- deterministic workflow smoke tests where feasible

**Environment Configuration:**
Use `.env`-style local configuration only for non-sensitive development settings, with secrets injected from local environment or OS keychain-backed mechanisms as needed.

**Monitoring and Logging:**
Use structured local logging for workflow traces, validation outcomes, import decisions, and recovery diagnostics. Logging should aid trust and troubleshooting, not just debugging.

Workflow runs should emit governed artifacts under the local artifacts tree so review, validation, and troubleshooting evidence remain inspectable after the command exits.

**Scaling Strategy:**
Defer scale-out architecture. MVP should scale by keeping workflows modular and deterministic, not by introducing services or distributed infrastructure.

### Workflow Verification & Observability Contract

Trust-sensitive workflows must share one verification contract across bootstrap, import, reconciliation, memory updates, and troubleshooting:
- every workflow run gets a stable `run_id`
- stage transitions are logged with structured event records
- validation output is persisted as an inspectable artifact for any ledger-changing or readiness-significant run
- deterministic smoke tests cover the standard happy path plus at least one blocked or validation-failure path
- CI must fail if core workflow contracts, result schemas, or deterministic smoke tests regress

This contract keeps cross-cutting readiness requirements visible in implementation instead of relying on convention.

### Decision Impact Analysis

**Implementation Sequence:**
1. initialize packaged Python project
2. establish CI baseline, workflow smoke tests, and structured run artifact conventions
3. define core typed domain models and service boundaries
4. implement file-backed memory store abstraction
5. implement ledger mutation planning and validation pipeline
6. implement import normalization adapters
7. implement reconciliation and approval workflows
8. wire CLI/skill orchestration to service layer

**Cross-Component Dependencies:**
- File-backed memory affects import normalization, reconciliation, and categorization flows
- No-public-API architecture reinforces CLI-first orchestration and internal typed service contracts
- No-auth local model increases the importance of git review, approval gates, and validation controls
- Deferred migration to PostgreSQL/vector retrieval requires keeping memory access abstract from day one

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:**
7 areas where AI agents could make different choices and create integration drift:
- memory file layout
- Python module and file naming
- command/result schemas
- ledger mutation flow
- error handling shape
- logging/audit conventions
- test placement and organization

### Naming Patterns

**Database Naming Conventions:**
No database tables exist in MVP. For future persistence-oriented concepts, all logical entity names use singular snake_case domain names such as `memory_entry`, `import_run`, and `mutation_plan`.

**API Naming Conventions:**
There is no public API in MVP. For internal automation payloads and CLI JSON output:
- use `snake_case` keys
- use stable explicit field names such as `status`, `error_code`, `message`, `details`
- avoid mixed casing or abbreviated keys

Examples:
- good: `import_run_id`, `ledger_path`, `validation_errors`
- avoid: `importRunId`, `ledgerPath`, `errs`

**Code Naming Conventions:**
- Python packages/modules: `snake_case`
- Python files: `snake_case.py`
- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- CLI commands: kebab-case command names are acceptable at the command surface, but map to `snake_case` Python implementations
- memory document keys: `snake_case`

Examples:
- good: `memory_store.py`, `ImportPlanner`, `build_mutation_plan`
- avoid: `memoryStore.py`, `importplanner`, `buildMutationPlan`

### Structure Patterns

**Project Organization:**
Organize by technical layer with strong domain boundaries, not by ad hoc utility growth.

Recommended pattern:
- `src/auto_bean/cli/` for command entrypoints only
- `src/auto_bean/application/` for workflow services and orchestration
- `src/auto_bean/domain/` for core models, policies, and domain errors
- `src/auto_bean/infrastructure/` for filesystem, git, Beancount, Fava, and external adapter integrations
- `src/auto_bean/memory/` for memory schemas and file-backed persistence
- `tests/` for top-level test suites grouped by layer or workflow

Rules:
- CLI code may parse input and render output, but must not implement business logic
- domain models must not depend on CLI or filesystem details
- infrastructure adapters must implement interfaces expected by application services
- shared helpers belong in the narrowest layer possible; do not create a generic `utils` dump

**File Structure Patterns:**
- memory files live under one governed directory tree, for example `.auto-bean/memory/`
- import artifacts live under one governed artifacts tree, separate from source ledger files
- generated review artifacts must never be mixed into domain source modules
- documentation about workflow contracts belongs in `docs/` or planning artifacts, not inline in random modules

### Format Patterns

**API Response Formats:**
For CLI JSON output and internal service result objects, use a consistent envelope:

Successful result:
```json
{
  "status": "ok",
  "data": {},
  "warnings": []
}
```

Failure result:
```json
{
  "status": "error",
  "error": {
    "code": "validation_failed",
    "message": "Ledger validation failed",
    "details": {}
  }
}
```

Rules:
- always include `status`
- use `data` only for successful payloads
- use structured `error.code` values, not freeform strings alone
- warnings are non-fatal and must not be mixed into errors

**Data Exchange Formats:**
- JSON fields: `snake_case`
- timestamps: ISO 8601 strings with timezone
- filesystem paths: stored as repo-relative paths where possible
- booleans: `true` / `false`
- nulls: use explicit `null`, not sentinel strings like `"none"` or `""`

### Communication Patterns

**Event System Patterns:**
No asynchronous event bus in MVP. Instead, use explicit workflow stage names and result objects.

Workflow stage naming:
- `parse_input`
- `normalize_records`
- `build_mutation_plan`
- `validate_plan`
- `request_approval`
- `apply_mutation`
- `run_post_validation`

If event-like records are needed for logs or audit trails:
- use `snake_case` event names
- include `event_name`, `timestamp`, `run_id`, and `context`

**State Management Patterns:**
State transitions must be explicit and immutable at the service boundary.
- services receive typed inputs
- services return typed outputs or typed domain errors
- services do not mutate shared global state
- workflow state that must persist goes into governed files, not ad hoc module-level caches

### Process Patterns

**Error Handling Patterns:**
Use typed domain errors with stable codes. At minimum:
- `validation_failed`
- `approval_required`
- `ambiguous_interpretation`
- `external_dependency_failed`
- `unsafe_mutation_blocked`
- `memory_schema_mismatch`
- `file_system_conflict`

Rules:
- errors must separate machine code from human explanation
- user-facing text must explain what happened and what needs review
- unexpected exceptions should be wrapped before crossing application boundaries
- no raw stack traces in normal CLI output

**Loading State Patterns:**
There is no frontend loading-state system in MVP. For long-running CLI workflows:
- report stage-based progress messages
- keep progress text deterministic and concise
- never imply that a mutation has been applied before approval and validation succeed

**Ledger Mutation Pattern:**
All ledger-changing workflows must follow the same pipeline:
1. read inputs
2. normalize into typed records
3. build mutation plan
4. produce diff/review artifact
5. validate plan and resulting ledger state
6. request explicit approval if risk or uncertainty exists
7. apply mutation
8. run post-apply validation
9. record audit outcome

No agent may skip directly from parsed input to file mutation.

### Enforcement Guidelines

**All AI Agents MUST:**
- use `snake_case` for Python files, internal payloads, and memory keys
- call application services instead of editing ledger files directly from CLI or skill logic
- persist reusable memory only through the governed memory abstraction
- return structured result or error objects at workflow boundaries
- follow the standard mutation pipeline for every ledger-changing action
- keep all primary financial and memory state local and file-backed in MVP

**Pattern Enforcement:**
- verify naming and import boundaries through Ruff and tests
- verify workflow contracts with unit tests for service results and domain errors
- verify deterministic workflow behavior and artifact emission with CI smoke tests
- review pattern violations as architecture issues, not style nits
- update patterns only by editing this architecture document first, then implementation guidance

### Pattern Examples

**Good Examples:**
- `src/auto_bean/application/import_service.py`
- `src/auto_bean/memory/file_memory_store.py`
- `build_mutation_plan(request: ImportRequest) -> MutationPlanResult`
- memory file path like `.auto-bean/memory/import_mappings/wise.yaml`
- CLI JSON response with `status`, `data`, `warnings`

**Anti-Patterns:**
- CLI command directly opening ledger files and writing changes
- mixed naming styles like `importRunId` inside Python domain models
- unversioned ad hoc memory JSON blobs spread across the repo
- returning bare dictionaries with inconsistent keys per command
- applying changes before validation or approval

## Project Structure & Boundaries

### Repository Model

This architecture uses a two-repository model:

- **Product repo (`auto-bean`)**: the software project where auto-bean is authored, tested, packaged, and released
- **User ledger repo**: the installed operating workspace where the agent interacts with the user's ledger, statements, memory, and review artifacts

This distinction is fundamental:
- the product repo is not the runtime finance workspace
- the user ledger repo is not the authoring source-of-truth for the product
- authored skills should not live under `.agents/skills/` in the product repo
- installed runtime skills should live under `.agents/skills/` in the user ledger repo

### Product Repo Structure

The product repo owns:
- authored skill source files
- shared policy markdown
- Python support code
- installation and upgrade logic
- workspace templates
- tests and release workflows

Recommended product repo structure:

```text
auto-bean/
├── README.md
├── pyproject.toml
├── uv.lock
├── .python-version
├── .gitignore
├── .env.example
├── .github/
│   └── workflows/
│       └── ci.yml
├── docs/
│   ├── quickstart.md
│   ├── architecture-overview.md
│   ├── ledger-concepts.md
│   ├── import-guides/
│   │   ├── pdf.md
│   │   ├── csv.md
│   │   └── excel.md
│   └── memory-model.md
├── skill_sources/
│   ├── auto-bean-init/
│   │   └── scripts/
│   ├── auto-bean-import/
│   │   └── scripts/
│   ├── auto-bean-apply/
│   │   └── scripts/
│   ├── auto-bean-memory/
│   │   └── scripts/
│   ├── auto-bean-query/
│   │   └── scripts/
│   ├── auto-bean-recover/
│   │   └── scripts/
│   └── shared/
├── workspace_template/
│   ├── README.md
│   ├── .gitignore
│   ├── .env.example
│   ├── beancheck.sh
│   ├── fava.sh
│   ├── ledger.beancount
│   ├── beancount/
│   ├── statements/
│   ├── docs/
│   ├── .agents/
│   │   └── plugins/
│   │       └── marketplace.json
│   └── .auto-bean/
├── src/
│   └── auto_bean/
│       ├── cli/
│       ├── application/
│       ├── domain/
│       ├── infrastructure/
│       └── memory/
├── scripts/
│   ├── bootstrap.sh
│   ├── run_fava.sh
│   ├── import_csv.py
│   ├── import_excel.py
│   ├── import_pdf.py
│   ├── validate_ledger.py
│   ├── generate_diff.py
│   └── write_memory.py
└── tests/
    ├── unit/
    ├── integration/
    ├── smoke/
    └── fixtures/
```

### Product Repo Boundaries

**Skill Source Boundaries:**
The source-of-truth skill content lives in `skill_sources/`, not in `.agents/skills/` inside the product repo.

Rules:
- `skill_sources/shared/` owns shared cross-cutting markdown policy
- skill behavior changes should begin in `skill_sources/` before support code changes
- the product repo must not contain live installed runtime skills under `.agents/skills/`

**Application Code Boundaries:**
Python code exists to support authored skill workflows, not replace them.
- `skill_sources/` owns authored workflow behavior
- `src/auto_bean/application/` owns reusable services
- `src/auto_bean/infrastructure/` owns side effects and integrations
- `skill_sources/**/scripts/` owns skill-local helper executables
- top-level `scripts/` owns packaging, validation, and development helpers for the product repo

**Workspace Template Boundaries:**
`workspace_template/` defines the skeleton of a fresh user ledger repo.
- it may contain placeholders and initial config
- it must not contain real user financial data
- it is not a live runtime workspace

### Runtime Boundaries

**Installed Skill Boundaries:**
Within the user ledger repo, the primary workflow boundary is the installed skill directory. Each installed skill owns:
- one user-facing `SKILL.md`
- one workflow coordinator markdown file
- step markdown files for deterministic execution
- local references/templates/examples specific to that skill
- optional skill-local helper scripts under `scripts/`

Rules:
- skills should depend on `.agents/skills/shared/` instead of duplicating shared policy
- skill markdown defines workflow behavior; supporting Python/scripts remain implementation helpers
- user-facing behavior should usually change in skill markdown before it changes in code

**Runtime Execution Boundaries:**
Installed skill workflows may call:
- an installed auto-bean support package available in the environment
- skill-local helper scripts bundled under the installed skill directories

The user ledger repo does not contain `src/auto_bean/`.

Python support code supports installed skill workflows; it does not replace them.
- installed `.agents/skills/` owns runtime agent interaction design
- the installed auto-bean package owns reusable services and integrations
- installed skill-local `scripts/` own narrow task-specific helpers

**Runtime Data Boundaries:**
- ledger truth remains in Beancount files
- reusable learned behavior remains under `.auto-bean/memory/`
- installed runtime skill definitions remain under `.agents/skills/`
- workflow artifacts remain under `.auto-bean/artifacts/`

### Runtime Mapping

The mappings below describe the runtime workspace. In the product repo, the authored equivalents live under `skill_sources/` and are installed into `.agents/skills/` during workspace initialization or upgrade.

**Feature/FR Mapping:**
- setup and workspace initialization:
  - `.agents/skills/auto-bean-init/`
  - `.agents/skills/auto-bean-init/scripts/`
  - installed auto-bean setup services
- statement import:
  - `.agents/skills/auto-bean-import/`
  - `.agents/skills/auto-bean-import/scripts/`
  - installed auto-bean import and importer services
- review, approval, rollback:
  - `.agents/skills/auto-bean-apply/`
  - `.agents/skills/auto-bean-recover/`
  - installed auto-bean review and validation services
- memory inspection and correction:
  - `.agents/skills/auto-bean-memory/`
  - `.agents/skills/auto-bean-memory/scripts/`
  - installed auto-bean memory services
- query/troubleshooting:
  - `.agents/skills/auto-bean-query/`
  - `.agents/skills/auto-bean-query/scripts/`
  - installed auto-bean query and diagnostics services

**Cross-Cutting Concerns:**
- approval logic:
  - `.agents/skills/shared/mutation-pipeline.md`
  - `.agents/skills/shared/mutation-authority-matrix.md`
  - installed auto-bean validation services
- audit and rollback:
  - `.agents/skills/auto-bean-apply/`
  - `.agents/skills/auto-bean-recover/`
  - installed auto-bean review and git services
- memory access:
  - `.agents/skills/shared/memory-access-rules.md`
  - `.agents/skills/auto-bean-memory/`
  - installed auto-bean memory services
- logging:
  - installed auto-bean logging services
  - `.auto-bean/logs/`
- configuration:
  - `.env.example`
  - `.auto-bean/state/`

### Integration Points

**Internal Communication:**
Primary flow:
1. authored skill content is installed from the product repo into the user ledger repo
2. agent enters an installed skill in the user ledger repo
3. installed `SKILL.md` routes into installed `workflow.md`
4. step markdown controls decisions and gathers context
5. skill invokes scripts or application services when needed
6. results are returned in the standard structured format

**External Integrations:**
- Beancount and Fava via infrastructure adapters or scripts
- git via infrastructure/git
- statement parsing helpers via scripts and importer adapters
- price lookup via infrastructure/pricing

**Data Flow:**
- source statements enter through importer adapters
- normalized transactions flow into reconciliation services
- mutation plans flow into validation and review
- approved plans flow into ledger writer + git review pipeline
- learned outcomes flow into governed memory files through approved memory update paths

### Product-to-Workspace Installation Model

The authored product reaches the runtime workspace through this flow:

1. author skills in `skill_sources/`
2. package Python support code from `src/auto_bean/`
3. create or upgrade a user ledger repo from `workspace_template/`
4. materialize authored skills into user `.agents/skills/`
5. preserve user-owned ledger files and governed runtime state during upgrades

Rules:
- product upgrades may replace installed skills and shared policy files
- product upgrades must not overwrite user financial data
- product upgrades must not overwrite durable memory without explicit migration logic
- normal ledger workflows never write back into the product repo

### User Ledger Repo Structure

Recommended runtime tree:

```text
my-ledger/
├── .agents/
│   ├── skills/
│   │   ├── auto-bean-init/
│   │   │   └── scripts/
│   │   ├── auto-bean-import/
│   │   │   └── scripts/
│   │   ├── auto-bean-apply/
│   │   │   └── scripts/
│   │   ├── auto-bean-memory/
│   │   │   └── scripts/
│   │   ├── auto-bean-query/
│   │   │   └── scripts/
│   │   ├── auto-bean-recover/
│   │   │   └── scripts/
│   └── plugins/
├── ledger.beancount
├── beancount/
│   ├── accounts/
│   ├── journals/
│   ├── prices/
│   └── config/
├── statements/
│   └── raw/
├── docs/
└── .auto-bean/
    ├── memory/
    ├── proposals/
    ├── artifacts/
    ├── state/
    └── cache/
```

Rules:
- `.agents/skills/` contains installed runtime skills derived from `skill_sources/`
- `.agents/skills/**/scripts/` contains skill-local helper scripts usable by that installed skill
- `beancount/` contains canonical ledger sources
- `statements/raw/` contains source statements and should not be rewritten
- `.auto-bean/memory/` contains durable operational memory
- `.auto-bean/proposals/` contains reviewable proposed changes
- `.auto-bean/artifacts/` contains diffs, validation reports, and run traces
- `.auto-bean/state/` contains lightweight workspace metadata
- `.auto-bean/cache/` is disposable and non-canonical

Operating model:
- the user ledger repo is the primary runtime workspace
- `ledger.beancount` is the stable entrypoint for Fava and validation
- account definitions stay separate from journals for cleaner review
- raw statements remain preserved for auditability and re-import
- all auto-bean-owned runtime state stays under `.auto-bean/`

Authority boundaries:
- installed `.agents/skills/**` may be changed by upgrade workflows, not routine ledger workflows
- only approved apply/recovery paths may modify `beancount/**`
- only the memory skill may modify `.auto-bean/memory/**`
- import workflows may write `.auto-bean/proposals/**` and `.auto-bean/artifacts/**`
- query workflows are read-only across the repo

### File Organization Patterns

**Markdown-First Product Files:**
These are first-class product assets, not supporting docs:
- `skill_sources/**/SKILL.md`
- `skill_sources/**/workflow.md`
- `skill_sources/**/steps/*.md`
- `skill_sources/**/references/*.md`
- `skill_sources/shared/*.md`

Installed runtime copies live in the user ledger repo under `.agents/skills/**`.

**Code-First Support Files:**
These exist in the product repo to make authored skills executable and reliable:
- `src/auto_bean/**`
- `skill_sources/**/scripts/**`
- `scripts/**`

**Test Organization:**
Tests should cover both:
- Python behavior in the product repo
- skill workflow integrity for authored markdown-driven flows

Smoke tests should include representative installed-skill workflows, not just isolated CLI commands.

### Development Workflow Integration

**Development Shape:**
Product development is primarily skill-driven. Most iteration should happen in authored markdown workflows, shared rules, examples, and templates, with helper code changing only when workflow capability requires it. Runtime use happens in user ledger repos with installed skills.

**Build Process Structure:**
There is no traditional frontend build. The effective build output is:
- installable Python support package
- validated authored skill source tree
- workspace template
- install/upgrade logic that materializes authored skills into user `.agents/skills/`
- repo-local scripts

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
The architecture is coherent. The technology choices, workflow model, and trust boundaries align with the actual operating model: a local-first, skill-driven Beancount workflow with Python support code. The revised structure resolves the earlier bias toward a conventional Python app and treats markdown skills as first-class product assets.

**Pattern Consistency:**
The patterns support the decisions well. Naming conventions, result envelopes, mutation pipeline rules, and authority boundaries all reinforce the CLI-and-skill model. The distinction between proposal-producing skills and mutation-authority skills is consistent across decisions, patterns, and structure.

**Structure Alignment:**
The structure supports the architecture. Skill directories own user-facing behavior, shared markdown files own cross-cutting policy, Python application code supports reusable execution logic, and governed local state is clearly separated into ledger files, memory files, and workflow artifacts.

### Requirements Coverage Validation ✅

**Feature Coverage:**
All major feature groups from the PRD have architectural support:
- setup and workspace initialization
- ledger creation and structure management
- statement import and normalization
- reconciliation and ambiguity handling
- review, approval, rollback, and recovery
- learned memory inspection and correction
- read-only query workflows
- external price lookup
- troubleshooting and trust recovery

**Functional Requirements Coverage:**
The architecture covers all FR categories through a combination of:
- skill-level workflow ownership
- supporting application services
- governed infrastructure adapters
- file-backed memory and artifact locations

Cross-cutting FRs such as validation, auditability, rollback, and approval are structurally supported rather than left to convention.

**Non-Functional Requirements Coverage:**
- Reliability is addressed through the mandatory mutation pipeline and validation boundaries.
- Privacy is addressed through local-first storage and minimal bounded external integrations.
- Determinism is addressed through typed workflow boundaries, governed memory, and stable result structures.
- Performance is addressed pragmatically by keeping the architecture local, modular, and free of unnecessary service complexity in MVP.

### Implementation Readiness Validation ✅

**Decision Completeness:**
Critical decisions are sufficiently documented for implementation. The main trust boundaries, storage model, workflow authority model, and project shape are all defined.

**Structure Completeness:**
The project structure is concrete enough to guide implementation. The skill tree, shared policy files, supporting modules, scripts, tests, and governed local state locations are identified.

**Pattern Completeness:**
The most important agent-conflict points are covered:
- naming
- result envelopes
- mutation authority
- memory access
- workflow sequencing
- separation of markdown workflow logic from supporting code

### Gap Analysis Results

**Critical Gaps:**
None identified that block implementation.

**Important Gaps:**
- The durable memory access contract should be documented explicitly as a required interface.
- The method for validating markdown workflow integrity should be defined in implementation planning.
- Recovery-path mutation authority should stay explicitly routed through approved apply/recovery flows.

**Nice-to-Have Gaps:**
- A dedicated shared markdown file for memory contract examples
- A small architecture note on how skill smoke tests should be structured
- A reference matrix showing which skills are read-only, proposal-only, or mutation-authority

### Validation Issues Addressed

The main issue found during validation was structural misalignment: an earlier draft treated Python code as the dominant product surface and markdown skills as supporting documentation. This was corrected by moving to a skill-first structure and defining authority boundaries around `init`, `import`, `apply`, `memory`, `query`, and `recover`.

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**✅ Architectural Decisions**
- [x] Critical decisions documented
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Safety and trust considerations addressed

**✅ Implementation Patterns**
- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented

**✅ Project Structure**
- [x] Complete skill-first directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements-to-structure mapping completed

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High

**Key Strengths:**
- skill-first product modeling
- explicit trust-boundary skill split
- governed memory model with future migration path
- strong safety pipeline for ledger mutations
- clear separation between workflow markdown, support code, and local state

**Areas for Future Enhancement:**
- formalize the memory service contract
- add explicit skill workflow validation strategy
- define the future RAG memory migration document when V2 planning begins

### Implementation Handoff

**AI Agent Guidelines:**
- treat skill markdown as the primary behavioral contract
- follow mutation authority boundaries exactly
- use shared policy markdown instead of duplicating cross-cutting rules
- keep durable memory access behind the governed memory abstraction
- route all ledger mutations through the standard mutation pipeline

**First Implementation Priority:**
Initialize the packaged Python foundation with `uv init --package auto-bean`, then scaffold the skill tree and shared policy markdown before building helper services.
