# System Architecture

This document is the living reference for the architecture of the text-to-SQL agent.

Current repository status:
- Core request orchestration and web UI flows (Chainlit and Streamlit) are implemented.
- User authentication and persistent conversation history are implemented over the conversation SQLite database.
- This document describes the current architecture and the intended boundaries for future changes.

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
- Use **functional core, imperative shell** as the main refactor direction for incremental internal improvements.

## Functional Core and Imperative Shell

The project uses a functional-first architecture for core business logic.

- Functional core:
  - `src/text_to_sql_agent/services/`
  - pure transformation helpers in `src/text_to_sql_agent/agents/`
  - reusable data-shaping helpers in `src/text_to_sql_agent/utils/`
- Imperative shell:
  - `src/text_to_sql_agent/ui/`
  - `src/text_to_sql_agent/repositories/`
  - runtime entrypoints and launchers

The detailed migration pattern, pilot modules, and rollout criteria are defined in `docs/RFC_FUNCTIONAL_STYLE.md`.

## High-Level Components

### Entry Point

`main.py` should remain thin.

Its responsibilities are:
- load configuration
- initialize services and graph or agent objects
- accept the runtime input channel
- hand off control to the application layer

Current runtime entrypoints:
- `main_chainlit.py` launches Chainlit web runtime.
- `main_streamlit.py` launches Streamlit web runtime.
- `main_terminal.py` provides terminal-mode interaction and schema shortcuts.
- `src/text_to_sql_agent/ui/chainlit_app.py` contains Chainlit callback wiring.
- `src/text_to_sql_agent/ui/streamlit_app.py` contains Streamlit interaction wiring.

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

Current schema ingestion node sequence is:
`load_connection_context` -> `introspect_schema` -> `normalize_schema` -> `build_schema_documents` -> `persist_schema_snapshot` -> `index_schema_embeddings`.

The graph state currently carries a canonical `normalized_schema` intermediate so the persistence and indexing nodes can share a single normalized view of the database.

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

Current auth/history services:
- `AuthService` (`src/text_to_sql_agent/services/auth_service.py`) owns register-or-login policy, Argon2 password hashing/verification, and account activity checks.
- `ConversationHistoryService` (`src/text_to_sql_agent/services/conversation_history_service.py`) is the read boundary for history with strict owner validation.

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

Current auth/history repositories:
- `SQLiteAuthRepository` persists accounts in `users` and provides username/user-id lookup, password-hash updates, and active-flag updates.
- `SQLiteSessionRepository` persists user/session conversation state (`users`, `conversations`, `messages`) and message history ordering.
- `conversation_db.bootstrap_schema()` initializes the auth/history schema and indices.

Current MCP repository boundary:
- `MCPClientRepository` defines the abstract repository contract for canonical MCP database tools (`mcp.db.execute`, `mcp.db.schema`, `mcp.db.health`).
- Concrete dialect adapters should implement this contract and return the typed request/response models from `src/text_to_sql_agent/models/mcp_contract.py`.
- `SQLiteMCPClientRepository` is the first concrete MCP adapter implementation and handles canonical execute/schema/health operations for SQLite.
- `PostgreSQLMCPClientRepository` is the PostgreSQL concrete MCP adapter implementation and handles canonical execute/schema/health operations for PostgreSQL.
- `AthenaMCPClientRepository` is the Athena concrete MCP adapter implementation and handles canonical execute/schema/health operations for Athena via an MCP tool invoker boundary.

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

Current auth/history configuration keys:
- `CONVERSATION_DB_PATH`
- `AUTH_AUTO_REGISTER_ON_FIRST_LOGIN`
- `AUTH_MIN_PASSWORD_LENGTH`

These are loaded through `load_conversation_auth_settings()`.

Current MCP runtime configuration keys:
- `MCP_SQLITE_ENDPOINT`, `MCP_SQLITE_TRANSPORT`, `MCP_SQLITE_CREDENTIALS_SOURCE`, `MCP_SQLITE_TIMEOUT_MS`
- `MCP_POSTGRESQL_ENDPOINT`, `MCP_POSTGRESQL_TRANSPORT`, `MCP_POSTGRESQL_CREDENTIALS_SOURCE`, `MCP_POSTGRESQL_TIMEOUT_MS`
- `MCP_ATHENA_ENDPOINT`, `MCP_ATHENA_TRANSPORT`, `MCP_ATHENA_CREDENTIALS_SOURCE`, `MCP_ATHENA_TIMEOUT_MS`

These are loaded through `load_mcp_runtime_settings()`.

Current MCP direction for query execution:
- SQLite, PostgreSQL, and Athena access is wired through a dialect-aware MCP-backed query execution factory.
- `query_execution_agent.execute_approved_query()` now resolves dialect-specific MCP adapters through `src/text_to_sql_agent/repositories/query_execution_factory.py`.
- Shared pre-execution policy enforcement now lives in `src/text_to_sql_agent/services/mcp_security_policy.py` and applies SELECT/WITH entrypoint constraints, denied-operation checks, and optional schema allowlists before MCP execution.
- Query execution emits structured `mcp_db_operation` audit events into `agent_events`, and these events are exposed through the existing `AuditTrail` assembly path.

## Auth and User-Scoped History Architecture

The web runtime uses username/password authentication with user-isolated history.

### Auth Flow

1. Chainlit calls `@cl.password_auth_callback` in `src/text_to_sql_agent/ui/chainlit_app.py`.
2. Callback delegates to `authenticate_with_password()` in `src/text_to_sql_agent/ui/auth_callbacks.py`.
3. `AuthService.authenticate_or_register()` validates credentials (or auto-registers if enabled).
4. On success, callback returns a `cl.User` containing stable `identifier` (`user_id`) and `metadata.username`.
5. On failure, callback returns `None`, and login is rejected.

### Conversation Persistence Model

Auth and history share one SQLite database (`conversation` DB path):

- `users`
  - auth identity (`user_id`, `username`, `password_hash`, `is_active`)
  - display metadata and timestamps
- `conversations`
  - `conversation_id`, owner `user_id`, title, optional `graph_thread_id`, metadata, timestamps
- `messages`
  - message role/content/metadata with ordered timestamps per conversation

This model supports:
- stable user identity across sessions,
- explicit conversation ownership,
- durable resume of message history and graph thread continuity.

### Ownership and Access Boundaries

User isolation is enforced at service boundary:

- listing: `ConversationHistoryService.list_user_conversations(user_id)` uses user-scoped repository list,
- loading: `ConversationHistoryService.load_user_conversation(user_id, conversation_id)` verifies `conversation.user_id == user_id`,
- violation path: raises `ConversationAccessError` and UI returns a safe denial message.

The Chainlit UI does not directly bypass these checks when opening saved conversations.

### Chainlit History UX Flow

On chat start (`@cl.on_chat_start`):
- session stores authenticated identity (`user_id`, `username`, `display_name`),
- initializes a fresh active `conversation_id`,
- renders user-scoped history actions.

History actions:
- `open_conversation`
  - validates ownership,
  - switches active conversation in session,
  - renders persisted messages,
- `new_conversation`
  - allocates new `conversation_id`,
  - keeps old history available in the list,
  - resets pending approval/edit state.

Follow-up messages are then routed through the currently active conversation state.

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

For Chainlit web flow, authenticated identity and active `conversation_id` are already present in session state before message handling.

2. Context preparation
Services load relevant schema information, table metadata, business rules, and any retrieval-augmented context.

3. Prompt assembly
Prompt utilities build the model input from the user request, schema context, and SQL constraints.

4. Planning or orchestration
A graph or agent decides which step runs next, such as clarification, schema lookup, SQL drafting, validation, or execution.

For schema ingestion specifically, the graph should materialize the normalized schema once, then reuse it for snapshot persistence and document/embedding generation.

5. SQL generation
The model produces a candidate SQL statement or structured intermediate representation.

6. Validation and guardrails
The system checks the generated output for allowed dialect rules, disallowed operations, and structural correctness before execution.

7. Query execution
A repository executes the approved SQL against the configured database, using MCP-backed adapters for supported dialects when enabled.

8. Result shaping
Services convert raw rows into a response that can include tabular data, summaries, and execution metadata.

9. Final response
The application returns the SQL, result set, and any explanation that should be exposed to the caller.

In web runtime, messages and approval events are persisted under the active conversation so the user can reopen and continue later.

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

### MCP Server Boundary for Database Access

For query execution and schema-access tools, the preferred runtime boundary is MCP server integration through dialect-aware repository adapters.

Architecture constraints for this boundary:
- adapters are provided per dialect (SQLite, PostgreSQL, Athena) behind a shared repository contract,
- orchestration and agent layers call the existing repository boundary and do not depend on transport details,
- SQL policy checks remain enforced before adapter execution,
- adapter outputs are normalized into project execution payloads and error contracts.

Operational baseline for MCP tools:
- read-only execution policy with deny-by-default behavior,
- explicit timeout and retry controls,
- structured audit events for allowed and denied operations,
- environment-based configuration and secret resolution.

Rollout sequence:
1. define tool contracts and runtime settings,
2. implement adapters and factory wiring,
3. harden with policy, observability, and integration tests.

### MCP Tool Contract (Canonical v1)

Canonical MCP tool names used by repository adapters:
- `mcp.db.execute` for approved read-only SQL execution,
- `mcp.db.schema` for schema metadata retrieval,
- `mcp.db.health` for adapter/server health probing.

Request contract baseline:
- shared metadata envelope with `request_id`, optional `conversation_id`, optional `user_id`, and `issued_at`,
- required `dialect` values: `sqlite`, `postgresql`, `athena`,
- required `database_id` for all tools,
- tool-specific payload fields:
  - execute: `sql`, `parameters`, `row_limit`, `timeout_ms`,
  - schema: `schema_names`, `table_names`, `include_views`,
  - health: `timeout_ms`.

Response contract baseline:
- success envelope with `status=success` and tool-specific `result` payload,
- error envelope with `status=error` and canonical error object,
- canonical error fields: `code`, `message`, `retriable`, `details`.

Error taxonomy baseline:
- `invalid_request`
- `forbidden_operation`
- `unauthorized`
- `unsupported_dialect`
- `tool_unavailable`
- `timeout`
- `execution_failed`
- `schema_not_found`
- `transport_error`

Typed source of truth for this contract is `src/text_to_sql_agent/models/mcp_contract.py`.
Repository-layer abstract source of truth for MCP adapter behavior is `src/text_to_sql_agent/repositories/mcp_client_repository.py`.

### MCP Setup Reference

Operational setup guidance for SQLite, PostgreSQL, and Athena MCP servers is documented in `README.md`.

Setup documentation covers:
- required infrastructure-side environment inputs per dialect,
- recommended authentication approach for local and production environments,
- run-command templates for starting external MCP servers,
- cheap preflight validation commands before application integration,
- contract-level validation order using `mcp.db.health`, `mcp.db.schema`, and `mcp.db.execute`.

Architectural assumption:
- MCP servers remain external infrastructure components and are not embedded into this repository runtime.

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
