# Changelog

All notable changes to this project will be documented in this file.

The format is intentionally simple and uses dated sections until versioned releases are introduced.

## 2026-05-18

### Changed

- Added SQL security guard agent (T-2026-05-18-045):
  - New `src/text_to_sql_agent/agents/security_guard_agent.py` with deterministic read-only security checks.
  - Security validation now blocks disallowed write/DDL operations and suspicious SQL patterns (inline/block comments, `UNION SELECT`, tautology `OR 1=1`).
  - Added `build_security_guard_node()` LangGraph adapter and wired it into `src/text_to_sql_agent/graphs/query_graph.py`, replacing the previous security-guard stub.
  - Added focused tests in `tests/text_to_sql_agent/agents/test_security_guard_agent.py`.

- Added SQL syntax validator agent (T-2026-05-18-044):
  - New `src/text_to_sql_agent/agents/syntax_validator_agent.py` with deterministic syntax and safety checks for generated SQL.
  - Validation now returns actionable errors for empty SQL, multiple statements, non-SELECT/WITH entrypoint, disallowed write/DDL operations, and unbalanced parentheses/quotes.
  - Added `build_syntax_validator_node()` LangGraph adapter and wired it into `src/text_to_sql_agent/graphs/query_graph.py`, replacing the previous syntax-validator stub.
  - Added focused tests in `tests/text_to_sql_agent/agents/test_syntax_validator_agent.py`.

- Added SQL generator agent (T-2026-05-18-043):
  - New `src/text_to_sql_agent/agents/sql_generator_agent.py` with deterministic read-only SQL generation from user question and schema context.
  - Added `SQLGenerationResult` output structure and `build_sql_generator_node()` LangGraph adapter.
  - SQL generator now detects basic intent (`count` vs `list`), selects a table from schema context, enforces safe limit for preview queries, and falls back to `SELECT 1 AS result LIMIT 1` when schema tables are unavailable.
  - Wired real SQL generator node into `src/text_to_sql_agent/graphs/query_graph.py`, replacing the previous stub implementation.
  - Added targeted tests in `tests/text_to_sql_agent/agents/test_sql_generator_agent.py`.

- Added schema context agent (T-2026-05-18-042):
  - New `src/text_to_sql_agent/agents/schema_context_agent.py` with `format_schema_context`, `build_schema_context`, and `build_schema_context_node`.
  - Schema formatted as compact text block: `-- Database: id (dialect)` header, `TABLE name / col type [PK/FK/NOT NULL]` body, with optional per-table filtering and stopword/punctuation normalization.
  - `build_schema_context_node(connection_config)` is a LangGraph adapter — returns a node function that populates `schema_context` and handles errors gracefully.
  - `build_query_graph()` extended with optional `connection_config` parameter so callers can inject real DB credentials without affecting test-time defaults.
  - Stub `node_schema_context` in `query_graph.py` replaced with the real agent; existing graph tests unaffected via default empty-config path.

- Added DB query orchestration graph (T-2026-05-18-041):
  - New `QueryState` TypedDict in `src/text_to_sql_agent/graphs/query_state.py` tracking all query pipeline fields.
  - New `build_query_graph()` in `src/text_to_sql_agent/graphs/query_graph.py` with stub nodes for schema context, SQL generation, syntax validation, security guard, human approval (LangGraph interrupt), MCP execution, analytics, and export.
  - Human approval gate uses `interrupt()` — graph pauses and waits for explicit approve/reject/edit before executing SQL.
  - Routing nodes enforce fail-fast on invalid syntax, blocked SQL, or user rejection.

- Added user identity and conversation history foundation (T-2026-05-18-040):
  - New `User`, `Conversation`, `ChatMessage`, `MessageRole` Pydantic models in `src/text_to_sql_agent/models/session.py`.
  - New `SessionRepository` abstract contract and `InMemorySessionRepository` in `src/text_to_sql_agent/repositories/session_repository.py`.
  - Each user gets a stable `user_id`; each conversation is scoped to a user; messages carry role, content, and metadata for SQL/approval context.
  - In-memory implementation is designed for drop-in replacement with a persistent backend (PostgreSQL/SQLite).

- Hardened schema shortcut parsing in `main_terminal.py` (T-2026-05-18-039):
  - `show/view schema for ...` now ignores filler words like `table`, `tables`, `for`, and `and`.
  - Trailing punctuation is stripped before schema lookup, so inputs like `view schema for table optins?` resolve correctly.

- Fixed terminal agent runtime compatibility in `main_terminal.py` (T-2026-05-18-038):
  - Migrated from deprecated `langgraph.prebuilt.create_react_agent` usage to `langchain.agents.create_agent`.
  - Replaced legacy `Tool` definitions with `StructuredTool` to align with current tool-call argument schema.
  - Added schema tool input adapter to support optional table filters and prevent `single-input tool` invocation errors.

- Started T-2026-05-18-037 secret placeholder resolution implementation:
  - Added `src/text_to_sql_agent/config/secrets.py` with `resolve_secret_placeholders()` for `[LOAD_FROM_SECRETS]` handling.
  - Added `FileSecretsProvider` and `AwsSecretsManagerProvider` scaffolding for local/test and production backends.
  - Added `tests/text_to_sql_agent/config/test_secrets.py` covering source precedence, production fail-fast, and local warning behavior.
  - Added `src/text_to_sql_agent/config/settings.py` and integrated `load_runtime_environment()` into `main_terminal.py` startup for real runtime placeholder resolution.
  - Added `tests/text_to_sql_agent/config/test_settings_runtime.py` for runtime env-file merge and backend resolution coverage.

- Refactored `main_terminal.py` (T-2026-05-18-036):
  - Replaced raw `sqlite3` introspection with `SQLiteIntrospectionProvider` + `normalize_raw_schema` from the established repository/service layers.
  - Database path now sourced from `SQLITE_PATH` env var instead of being hardcoded.
  - Read-only SQL enforcement: `query_database()` rejects non-SELECT inputs before any database access.
  - `get_db_schema()` accepts an optional table-name filter; terminal supports `schema [<table>…]` for targeted schema inspection.
  - Migrated terminal agent execution to `langgraph.prebuilt.create_react_agent` (LangChain v1 compatible), replacing the removed `AgentExecutor` import path.
  - Added OpenAI key env aliases (`OPENAI_API_KEY`, `OPENAI_KEY`, `OPENAI_TOKEN`) for terminal startup compatibility.
  - Added natural-language schema shortcuts (`view full database schema`, `show schema for ...`) that do not require LLM credentials.
  - Agent executor lazily initialised on first natural-language query so schema commands work without `OPENAI_API_KEY`.
  - Loguru integrated at WARNING level on stderr.
  - Removed `show_graph` stub tool and `graph` terminal shortcut.

### Added

- Thin schema reader agent entrypoint in `src/text_to_sql_agent/agents/schema_reader_agent.py`:
  - Converts `SchemaRefreshRequest` objects into initial `SchemaReadState` payloads.
  - Invokes the compiled schema ingestion graph with explicit `connection_config_ref` wiring.
  - Supports explicit request ID overrides for callers that already have request correlation data.
- Agent tests in `tests/text_to_sql_agent/agents/test_agents_scaffold.py`:
  - Covers state construction, graph invocation, and request ID override behavior.
- Updated `src/text_to_sql_agent/agents/__init__.py` to export the agent entrypoint helpers.

- Compiled LangGraph schema ingestion workflow in `src/text_to_sql_agent/graphs/schema_graph.py`:
  - Wires the schema ingestion nodes into a `StateGraph` with explicit retry, failure, and completion transitions.
  - Supports dependency injection for connection resolution, introspection providers, snapshot persistence, vector storage, and embedding generation.
  - Complements the existing node functions with terminal success and failure states that set workflow completion timestamps.
- Graph workflow tests in `tests/text_to_sql_agent/graphs/test_graphs_scaffold.py`:
  - Covers the full happy path, a transient retry path, and the exhausted-retry failure path.
- Updated `src/text_to_sql_agent/graphs/__init__.py` to export the compiled graph builder.

## 2026-05-15

### Added

- LangGraph schema ingestion node functions in `src/text_to_sql_agent/graphs/schema_nodes.py`:
  - Connection context loading, provider-based introspection, schema normalization, document building, snapshot persistence, and embedding indexing.
  - Added `normalized_schema` to `SchemaReadState` as the canonical intermediate schema payload.
- Schema indexing service in `src/text_to_sql_agent/services/schema_indexing.py`:
  - `index_schema_embeddings()` turns semantic schema documents into embedding records and persists them through a vector store repository.
  - Uses an injected embedder callable and stable default embedding ID generation.
  - Handles empty document lists without writing any records.
- Abstract vector store repository interface in `src/text_to_sql_agent/repositories/vector_store_repository.py`:
  - `VectorStoreRepository` defines the storage and retrieval contract for embedded schema records.
  - Includes upsert, similarity search, and snapshot-scoped deletion operations.
- Schema document building service in `src/text_to_sql_agent/services/schema_document_builder.py`:
  - `build_schema_documents()` converts canonical database schemas into semantic documents.
  - Generates table, column-group, and relationship documents with deterministic IDs and readable content.
  - Preserves domain tags and metadata while ordering columns by ordinal position.
- Schema snapshot repository in `src/text_to_sql_agent/repositories/schema_snapshot_repository.py`:
  - `SchemaSnapshotRepository` persists canonical schema snapshots as JSON files.
  - Supports save, load, list, and delete operations with `SchemaSnapshotRef` metadata.
  - Creates the storage directory automatically on initialization.
- Schema normalization service in `src/text_to_sql_agent/services/schema_normalization.py`:
  - `normalize_raw_schema()` converts raw introspection output into canonical `DatabaseSchema`.
  - Generates stable snapshot IDs, normalizes table kinds and data types, resolves PK/FK flags, and deduplicates foreign keys.
- Introspection provider factory and registry in `src/text_to_sql_agent/repositories/provider_factory.py`:
  - `PROVIDER_REGISTRY` maps supported dialects to provider classes.
  - `normalize_dialect()` resolves aliases and casing for dialect lookup.
  - `get_introspection_provider()` returns the matching provider instance or raises for unsupported dialects.
- PostgreSQL schema introspection provider in `src/text_to_sql_agent/repositories/postgresql_provider.py`:
  - `PostgresIntrospectionProvider`: concrete implementation using `information_schema` and `pg_catalog`.
  - System schema exclusion, primary/unique/foreign key extraction, index parsing.
  - Added `psycopg2-binary` dependency for PostgreSQL connectivity.
- SQLite schema introspection provider in `src/text_to_sql_agent/repositories/sqlite_provider.py`:
  - `SQLiteIntrospectionProvider`: concrete implementation reading schema via sqlite_master, PRAGMA queries.
  - Handles tables, views, columns (with proper PK nullability), foreign keys (with cascade rules), indexes, and default values.
  - Supports in-memory databases (":memory:") and file-based databases.
- Abstract schema introspection provider interface in `src/text_to_sql_agent/repositories/introspection_provider.py`:
  - `SchemaIntrospectionProvider`: abstract base class defining the contract for dialect-specific schema readers.
  - Single method: `introspect(database_id, connection_config) -> RawIntrospectionResult`.
  - Serves as foundation for PostgreSQL, MySQL, SQLite, MSSQL, and other dialect adapters.
- LangGraph state definition in `src/text_to_sql_agent/graphs/state.py`:
  - `SchemaReadState`: TypedDict for schema ingestion workflow state management. Tracks request identity, parameters, runtime context, step outputs (as references), control flow, and observability.
  - Uses `Annotated[list[str], add_messages]` for error and warning lists to support LangGraph message reducers.
- Lifecycle and operational Pydantic models in `src/text_to_sql_agent/models/lifecycle.py`:
  - `SchemaSnapshotRef`: tracks schema snapshot lifecycle with status (fresh, stale, indexing, indexed, failed).
  - `SchemaRefreshRequest`: specifies schema refresh scope with refresh modes (full, incremental, metadata_only) and optional table targeting.
- Document and embedding Pydantic models in `src/text_to_sql_agent/models/document.py`:
  - `SchemaDocument`: represents a semantic document chunk with granularity (table, column_group, relationship), human-readable content for embedding, domain tags, and metadata.
  - `SchemaEmbeddingRecord`: represents a computed embedding vector linked to a document, database, and snapshot.
- Canonical schema Pydantic models: `ForeignKeySchema`, `ColumnSchema`, `TableSchema`, `DatabaseSchema` in `src/text_to_sql_agent/models/schema.py`. These are the normalized internal contract used across all layers.
- Raw introspection Pydantic models: `RawColumnMeta`, `RawForeignKeyMeta`, `RawIndexMeta`, `RawTableMeta`, `RawIntrospectionResult` in `src/text_to_sql_agent/models/introspection.py`. These are the vendor-specific metadata shapes before normalization.
- `src/text_to_sql_agent/models/__init__.py` package init exporting all raw introspection models.

### Changed

- Updated `.env.test` so SQLite test runs use `tests/text_to_sql_agent/db/test_database.db` instead of an in-memory database.
- Added a config test that locks the test environment to the repository-backed SQLite database path.

## 2026-05-11

### Added

- Repository-specific working instructions in `.github/copilot-instructions.md`.
- An explicit English-only rule for documentation, comments, and project-facing technical explanations.
- Project tracking files: `docs/TASKS.md`, `docs/WORKLOG.md`, and `docs/DECISIONS.md`.
- A dedicated project changelog to summarize notable repository changes.
- Initial architecture document in `docs/ARCHITECTURE.md` describing the target system design.
- VS Code configuration in `.vscode/settings.json` for automatic `venvtext2sql` activation.
- Explicit environment setup and dependency management instructions.
- Comprehensive environment-based configuration system:
  - `.env` template file with 70+ configuration keys covering all project aspects.
  - `.env.dev` for local development with localhost and debug settings.
  - `.env.prod` for production with remote hosts and strict security (not committed).
  - `.env.test` for CI/CD and testing with in-memory databases and mocked services.
  - Configuration categories: project settings, database drivers (SQLite, PostgreSQL, Athena, MySQL), LLM parameters, caching, feature flags, rate limiting, secrets management, observability, audit logging, migrations, validation, multi-tenant support, API, and monitoring.
  - Updated `.gitignore` to protect `.env`, `.env.prod`, and `.env.local` from accidental commits.
- Production-ready structured logging using loguru (`loguru==0.7.3`):
  - `src/text_to_sql_agent/config/logging.py` with `LoggingConfig` (Pydantic model) and `setup_logging()` function.
  - Support for text (colored, readable) and JSON (production) output formats.
  - Per-module log level configuration (agents, services, repositories, graphs, models, prompts).
  - File rotation with gzip compression and configurable retention policies.
  - Flexible output modes: stdout, file, or combined.
  - Context binding support for request tracing.
- Specialized GitHub Copilot agents (`docs/AGENTS.md`):
  - **Architect Agent** (`.architect.instructions.md`): System architecture design and review.
  - **Task Manager Agent** (`.taskmanager.instructions.md`): Task planning and project organization.
  - **Developer Agent** (`.developer.instructions.md`): Code implementation and feature development.
  - **Tester Agent** (`.tester.instructions.md`): Quality assurance and comprehensive testing.
  - **Documentarian Agent** (`.documentarian.instructions.md`): Documentation and technical writing.
  - Complete agent usage guide with example workflows and prompts.
- SQL dialect prompt scope baseline:
  - Added `docs/SQL_DIALECT_SCOPE.md` with a concise comparison matrix for PostgreSQL, MySQL, Athena, and SQLite.
  - Added typed prompt-scope contract in `src/text_to_sql_agent/prompts/dialect_scope.py`.
  - Added `tests/test_dialect_scope.py` to validate matrix completeness, lookup behavior, and read-only example constraints.
- MVP prompt manifest contract:
  - Added typed contract in `src/text_to_sql_agent/prompts/prompt_manifest.py` for minimal read-only SQL safety and rollout control.
  - Added `docs/PROMPT_MANIFEST_MVP.md` with the required fields and validation rules.
  - Added `tests/test_prompt_manifest.py` for contract validation coverage.
- Enterprise prompt manifest contract:
  - Extended `src/text_to_sql_agent/prompts/prompt_manifest.py` with tenant isolation, audit metadata, approval workflow, and rollout policy level models.
  - Added `docs/PROMPT_MANIFEST_ENTERPRISE.md` with enterprise field definitions and policy constraints.
  - Added `tests/test_prompt_manifest_enterprise.py` for enterprise validation coverage.
- Prompt change request governance process:
  - Added typed process contract in `src/text_to_sql_agent/prompts/change_request.py`.
  - Added `docs/PROMPT_CHANGE_REQUEST_PROCESS.md` with required fields, review flow, required approvers, and emergency hotfix path.
  - Added `tests/test_prompt_change_request.py` to validate approval gates and hotfix postmortem rules.
- Prompt user override policy:
  - Added typed override boundary contract in `src/text_to_sql_agent/prompts/override_policy.py`.
  - Added `docs/PROMPT_USER_OVERRIDE_POLICY.md` defining customizable and immutable prompt sections.
  - Added `tests/test_prompt_override_policy.py` validating immutable enforcement, allowed sections, and payload size boundaries.
- Prompt storage and version registry design:
  - Added typed storage/registry contract in `src/text_to_sql_agent/prompts/storage_registry.py`.
  - Added `docs/PROMPT_STORAGE_VERSION_REGISTRY.md` with external storage and version pointer rules.
  - Added `tests/test_prompt_storage_registry.py` validating checksum, URI scheme, and pointer/status consistency.
- Prompt metrics and evaluation gates:
  - Added typed gate contract in `src/text_to_sql_agent/prompts/evaluation_gates.py`.
  - Added `docs/PROMPT_EVALUATION_GATES.md` with default metric thresholds and promotion decision rules.
  - Added `tests/test_prompt_evaluation_gates.py` validating hard-fail behavior, missing metrics, and sample-size warnings.
- Mirrored test package layout:
  - Added mirrored test directory skeleton under `tests/text_to_sql_agent/` for `agents`, `config`, `graphs`, `models`, `prompts`, `repositories`, `services`, and `utils`.
  - Added `tests/text_to_sql_agent/README.md` documenting test placement rules.
  - Updated `.github/copilot-instructions.md`, `.tester.instructions.md`, and `docs/AGENTS.md` to enforce mirrored `tests`/`src` structure for future test files.

### Changed

- Documentation workflow now requires recording tasks in `docs/TASKS.md`, implementation history in `docs/WORKLOG.md`, durable decisions in `docs/DECISIONS.md`, and notable project changes in `docs/CHANGELOG.md`.
- The canonical changelog location was moved from the repository root to `docs/CHANGELOG.md`.
- Updated repository instructions to document `venvtext2sql` as the canonical virtual environment and `uv` as the package manager.
- Updated VS Code Python configuration to always show the selected interpreter in the status bar, making the canonical `venvtext2sql` environment visible during development.