# System Architecture

This document is the living reference for the architecture of the text-to-SQL agent.

Current repository status:
- The package structure is defined.
- The implementation is still minimal.
- This document therefore describes the target architecture the codebase is expected to follow as development continues.

## Goal

The system converts a natural language analytics request into a safe and explainable SQL workflow.

The high-level outcome is:
1. accept a user question
2. understand intent and database context
3. generate constrained SQL
4. execute the query through a controlled repository layer
5. return results and supporting explanation

## Architectural Principles

- Keep orchestration separate from database access.
- Isolate prompt construction from business logic.
- Validate structured inputs and outputs with typed models.
- Prefer explicit workflow steps over hidden agent behavior.
- Make SQL generation observable, testable, and easy to constrain.
- Keep the entry point thin and move real logic into `src/text_to_sql_agent/`.

## High-Level Components

### Entry Point

`main.py` should remain thin.

Its responsibilities are:
- load configuration
- initialize services and graph or agent objects
- accept the runtime input channel
- hand off control to the application layer

### Agents Layer

`src/text_to_sql_agent/agents/`

This layer owns agent-specific behavior such as:
- user-facing orchestration logic
- step selection when an LLM-based agent is used
- packaging model outputs into structured application actions

Agents should not talk directly to the database driver when a service or repository boundary already exists.

### Graphs Layer

`src/text_to_sql_agent/graphs/`

This layer defines the explicit workflow for request handling.

Expected responsibilities:
- sequence the major steps of the request lifecycle
- manage retries or fallbacks
- pass structured state between steps
- provide a deterministic backbone around model calls

If LangGraph is used as intended, this layer should become the main execution spine of the application.

### Services Layer

`src/text_to_sql_agent/services/`

This layer contains business logic that is independent from transport or storage details.

Typical responsibilities:
- schema retrieval and summarization
- SQL generation coordination
- SQL validation or post-processing
- result shaping for downstream consumers
- integration with embeddings, vector search, or LLM clients

Services may call repositories and prompt builders, but should avoid owning UI or CLI concerns.

### Repositories Layer

`src/text_to_sql_agent/repositories/`

This layer is the controlled boundary to the database and persistence systems.

Expected responsibilities:
- open and manage database sessions or connections
- execute parameterized or generated SQL
- read schema metadata
- isolate SQLAlchemy or psycopg specific details
- centralize low-level data access error handling

This boundary is important because it creates a single place for execution controls and auditing.

### Models Layer

`src/text_to_sql_agent/models/`

This layer defines typed contracts for the system.

Expected model categories:
- request models
- graph state models
- SQL generation inputs and outputs
- schema metadata representations
- result payloads
- error and validation payloads

Pydantic models should be preferred where validation and serialization matter.

### Prompts Layer

`src/text_to_sql_agent/prompts/`

This layer stores reusable prompt templates and prompt-building utilities.

Expected responsibilities:
- separate prompt text from orchestration logic
- inject schema context safely
- keep SQL generation instructions consistent
- support prompt reuse across services and graphs
- encode dialect-specific prompt constraints (PostgreSQL, MySQL, Athena, SQLite)

Dialect scope baseline for prompts is documented in `docs/SQL_DIALECT_SCOPE.md` and represented in typed form in `src/text_to_sql_agent/prompts/dialect_scope.py`.
MVP prompt manifest contract is documented in `docs/PROMPT_MANIFEST_MVP.md` and represented in typed form in `src/text_to_sql_agent/prompts/prompt_manifest.py`.
Enterprise prompt manifest contract is documented in `docs/PROMPT_MANIFEST_ENTERPRISE.md` and represented in typed form in `src/text_to_sql_agent/prompts/prompt_manifest.py`.
Prompt update governance process is documented in `docs/PROMPT_CHANGE_REQUEST_PROCESS.md` and represented in typed form in `src/text_to_sql_agent/prompts/change_request.py`.
Prompt user override boundaries are documented in `docs/PROMPT_USER_OVERRIDE_POLICY.md` and represented in typed form in `src/text_to_sql_agent/prompts/override_policy.py`.
Prompt storage and version registry design is documented in `docs/PROMPT_STORAGE_VERSION_REGISTRY.md` and represented in typed form in `src/text_to_sql_agent/prompts/storage_registry.py`.
Prompt metrics and evaluation gates are documented in `docs/PROMPT_EVALUATION_GATES.md` and represented in typed form in `src/text_to_sql_agent/prompts/evaluation_gates.py`.

### Config Layer

`src/text_to_sql_agent/config/`

This layer defines runtime configuration.

Expected responsibilities:
- environment loading
- application settings
- model provider settings
- database connection settings
- feature flags and operational limits

Configuration should come from the environment or explicit settings objects, not from hardcoded values.

### Utils Layer

`src/text_to_sql_agent/utils/`

This layer should contain only small shared helpers that do not deserve their own higher-level module.

Examples:
- text normalization helpers
- SQL formatting helpers
- common tracing helpers
- small validation utilities

## Request Lifecycle

A typical request should follow this flow:

1. Input intake
The application receives a natural language question and optional execution context.

2. Context preparation
Services load relevant schema information, table metadata, business rules, and any retrieval-augmented context.

3. Prompt assembly
Prompt utilities build the model input from the user request, schema context, and SQL constraints.

4. Planning or orchestration
A graph or agent decides which step runs next, such as clarification, schema lookup, SQL drafting, validation, or execution.

5. SQL generation
The model produces a candidate SQL statement or structured intermediate representation.

6. Validation and guardrails
The system checks the generated output for allowed dialect rules, disallowed operations, and structural correctness before execution.

7. Query execution
A repository executes the approved SQL against the configured database.

8. Result shaping
Services convert raw rows into a response that can include tabular data, summaries, and execution metadata.

9. Final response
The application returns the SQL, result set, and any explanation that should be exposed to the caller.

## Cross-Cutting Concerns

### Safety and SQL Constraints

The system should enforce strong controls around generated SQL.

Expected controls:
- restrict statements to approved query types when read-only mode is required
- validate table and column access against known schema metadata
- reject unsafe or destructive statements by default
- keep execution limits and timeouts configurable

### Observability

The system should capture enough information to debug model-driven behavior.

Useful signals include:
- prompt version or prompt source
- selected schema context
- generated SQL
- validation failures
- execution timing
- query errors and fallback paths

### Testability

The architecture should support focused tests at each layer.

Recommended test boundaries:
- models and validators
- prompt builders
- dialect scope matrix integrity and read-only example constraints
- prompt manifest contract validation (safety placeholders, read-only mode, rollout rules)
- enterprise manifest governance validation (tenant isolation, audit metadata, approvals, policy-level rollout constraints)
- prompt change request governance validation (required fields, approver gates, emergency hotfix postmortem path)
- user override boundary validation (allowed sections, immutable safety sections, payload size, rationale requirement)
- storage/registry validation (external storage config, checksum integrity, status pointers, ownership metadata)
- evaluation gate validation (validity, execution success, policy violation, leakage, and sample-size warnings)
- service logic with mocked repositories and model clients
- repository behavior against controlled test databases where appropriate
- graph transitions and state updates

## External Integrations

Based on the current dependencies, the architecture is expected to integrate with:
- LLM providers through LangChain and LangChain OpenAI
- workflow orchestration through LangGraph
- relational databases through SQLAlchemy and psycopg
- optional retrieval or memory support through ChromaDB
- local configuration through environment-based settings

## Future Extension Points

The architecture should support future additions without breaking the layer boundaries.

Likely extension points:
- multi-database support
- schema caching
- semantic table retrieval
- query explanation generation
- human approval before execution
- benchmark and evaluation tooling
- notebook or API-based interfaces

## Documentation Rule

When implementation changes the actual system shape, update this file so it continues to describe the real or intended architecture clearly.
