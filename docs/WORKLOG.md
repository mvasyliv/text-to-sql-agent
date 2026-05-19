# Work Log

This file stores a chronological log of work performed on the project.

Rules:
- Keep entries concise and factual.
- Reference task IDs from `docs/TASKS.md`.
- Write every entry in English.

## 2026-05-18

### T-2026-05-18-051 - Build Chainlit UI flow for DB assistant

- Added `src/text_to_sql_agent/ui/` package with dedicated UI integration layer:
  - `chainlit_app.py` with Chainlit chat handlers for message flow and action callbacks.
  - `handlers.py` with deterministic orchestration helpers (`build_ui_runtime`, `start_query_turn`, `resume_query_turn`, export helpers) over the existing LangGraph query pipeline.
  - `renderers.py` with SQL preview rendering, markdown table rendering, and chart-spec to Plotly figure conversion.
- Implemented approval UI flow:
  - SQL preview message is shown before execution.
  - Action callbacks support `approve`, `reject`, and `edit` behavior.
  - Edit flow captures revised SQL from the next user message and resumes the paused graph checkpoint.
- Implemented result UI flow:
  - Tabular result rendering from `execution_result` rows.
  - One-shot chart rendering based on `chart_spec`.
  - Export actions for CSV and JSON using existing export service.
- Updated runtime/dependency wiring:
  - Added `chainlit` dependency in `pyproject.toml` and refreshed `uv.lock` via `uv add`.
  - Updated `main.py` with a thin entrypoint note for launching Chainlit app.
- Added tests:
  - `tests/text_to_sql_agent/ui/test_handlers.py` (3 cases)
  - `tests/text_to_sql_agent/ui/test_renderers.py` (3 cases)
- Validation:
  - `uv run pytest -q tests/text_to_sql_agent/ui/test_handlers.py tests/text_to_sql_agent/ui/test_renderers.py tests/text_to_sql_agent/graphs/test_query_graph.py` -> 18 passed.
  - `uv run ruff check src/text_to_sql_agent/ui tests/text_to_sql_agent/ui main.py docs` -> all checks passed.

### T-2026-05-18-050 - Implement insights agent over query results

- Created `src/text_to_sql_agent/services/query_insights.py`:
  - Added deterministic `build_query_insight(execution_result, chart_spec)` service.
  - Added `QueryInsightResult` contract containing concise narrative insight text.
  - Insight logic summarizes row/column volume and chart metadata (type + plotted points), with explicit no-rows fallback.
- Created `src/text_to_sql_agent/agents/insights_agent.py`:
  - Added `build_insights_node()` LangGraph adapter.
  - Node consumes `execution_result` and `chart_spec` only, returns `insight_text`, and fails safely if input payload is missing.
- Updated exports:
  - `src/text_to_sql_agent/services/__init__.py` now exports `QueryInsightResult` and `build_query_insight`.
  - `src/text_to_sql_agent/agents/__init__.py` now exports `build_insights_node`.
- Updated `src/text_to_sql_agent/graphs/query_graph.py`:
  - Inserted insights step between analytics and export (`analytics -> insights -> export`).
- Added tests:
  - `tests/text_to_sql_agent/services/test_query_insights.py` (4 cases)
  - `tests/text_to_sql_agent/agents/test_insights_agent.py` (2 cases)
  - Updated `tests/text_to_sql_agent/graphs/test_query_graph.py` to assert `insight_text` presence on happy path.
- Validation:
  - `pytest` on new insights tests + existing query graph tests -> 18 passed.
  - `ruff check` on modified files -> all checks passed.

### T-2026-05-18-049 - Implement analytics agent for one-shot charts

- Created `src/text_to_sql_agent/services/query_analytics.py`:
  - Added `build_one_shot_chart(execution_result, max_points)` to derive one chart from an already executed tabular result.
  - Added `QueryAnalyticsResult` with `chart_spec` and `insight_text`.
  - Implemented deterministic strategy:
    - categorical + numeric -> bar chart of `sum(numeric)` by category
    - categorical only -> bar chart of frequency counts
    - numeric only -> one-shot line chart
    - empty/fallback handling with explicit insight text
- Created `src/text_to_sql_agent/agents/analytics_agent.py`:
  - Added `build_analytics_node()` LangGraph adapter.
  - Node consumes `execution_result` only, outputs `chart_spec` + `insight_text`, and reports failures with `status=failed`.
- Updated exports:
  - `src/text_to_sql_agent/services/__init__.py` now exports `QueryAnalyticsResult` and `build_one_shot_chart`.
  - `src/text_to_sql_agent/agents/__init__.py` now exports `build_analytics_node`.
- Updated `src/text_to_sql_agent/graphs/query_graph.py`:
  - Replaced analytics stub node with `node_analytics = build_analytics_node()`.
- Added tests:
  - `tests/text_to_sql_agent/services/test_query_analytics.py` (6 cases)
  - `tests/text_to_sql_agent/agents/test_analytics_agent.py` (3 cases)
- Validation:
  - `pytest` on new analytics tests + existing query graph tests -> 21 passed.
  - `ruff check` on modified files -> all checks passed.

### T-2026-05-18-048 - Implement data export agent

- Created `src/text_to_sql_agent/services/query_result_export.py`:
  - Added `export_query_result(execution_result, export_format, output_dir)` for file export from already available execution payload.
  - Supported export formats: CSV, JSON, and optional XLSX (`openpyxl` required).
  - Added strict format validation, automatic output path generation, and normalized content structure.
- Created `src/text_to_sql_agent/agents/export_agent.py`:
  - Added `export_execution_result()` agent helper over service layer.
  - Added `build_export_node()` LangGraph adapter that exports from `execution_result` only (no SQL re-execution).
  - Node supports state override `export_format` with configurable default.
- Updated exports:
  - `src/text_to_sql_agent/services/__init__.py` now exports `export_query_result`.
  - `src/text_to_sql_agent/agents/__init__.py` now exports `build_export_node` and `export_execution_result`.
- Updated `src/text_to_sql_agent/graphs/query_graph.py`:
  - Replaced export stub with `node_export = build_export_node()`.
- Added tests:
  - `tests/text_to_sql_agent/services/test_query_result_export.py` (4 cases)
  - `tests/text_to_sql_agent/agents/test_export_agent.py` (4 cases)
- Validation:
  - `pytest` on new export tests + existing query graph tests -> 20 passed.
  - `ruff check` on modified files -> all checks passed.

### T-2026-05-18-047 - Implement query execution agent

- Created `src/text_to_sql_agent/agents/query_execution_agent.py`:
  - Added `is_read_only_query()` read-only guard (`SELECT`/`WITH`/`EXPLAIN`).
  - Added `execute_approved_query()` with dialect-based repository lookup and standardized payload (`database_id`, `dialect`, `sql`, `rows`, `columns`, `row_count`).
  - Added `build_query_execution_node(connection_config)` LangGraph adapter with two modes:
    - real mode when `connection_config` is provided
    - stub fallback mode (for graph tests and dry-runs) when config is absent
- Added execution repository layer:
  - `src/text_to_sql_agent/repositories/query_execution_repository.py` (abstract contract)
  - `src/text_to_sql_agent/repositories/sqlite_query_execution_repository.py` (SQLite implementation)
  - `src/text_to_sql_agent/repositories/query_execution_factory.py` (dialect factory)
- Updated exports:
  - `src/text_to_sql_agent/agents/__init__.py` with query execution symbols.
  - `src/text_to_sql_agent/repositories/__init__.py` with query execution repository/factory symbols.
- Updated `src/text_to_sql_agent/graphs/query_graph.py`:
  - Replaced query executor stub with `build_query_execution_node(connection_config)`.
  - Graph now executes approved SQL via repository path when config is available.
- Added tests:
  - `tests/text_to_sql_agent/agents/test_query_execution_agent.py` (10 cases)
  - `tests/text_to_sql_agent/repositories/test_query_execution_repository.py` (4 cases)
- Validation:
  - `pytest` on new agent + repository tests and existing query graph tests -> 22 passed.
  - `ruff check` on all modified files -> all checks passed.

### T-2026-05-18-046 - Implement human approval gate

- Created `src/text_to_sql_agent/agents/human_approval_agent.py`:
  - Added `HumanApprovalDecision` and `normalize_approval_decision()` for explicit action normalization.
  - Supported approval actions: `approve`, `reject`/`cancel`, and `edit`.
  - Added `build_human_approval_node()` LangGraph adapter that pauses via interrupt payload and applies strict state transitions.
- State transition behavior implemented:
  - `approve` -> `human_approved=True`, `status=executing`.
  - `edit` -> `human_approved=True`, `edited_sql=<user_sql>`, `status=executing`.
  - `reject/cancel/unknown` -> `human_approved=False`, `status=cancelled`.
- Updated `src/text_to_sql_agent/graphs/query_graph.py`:
  - Replaced inline human approval node implementation with `node_human_approval = build_human_approval_node()`.
- Updated `src/text_to_sql_agent/agents/__init__.py` exports:
  - Added `HumanApprovalDecision`, `build_human_approval_node`, and `normalize_approval_decision`.
- Added tests `tests/text_to_sql_agent/agents/test_human_approval_agent.py` (9 cases):
  - Decision normalization cases for approve/reject/cancel/edit/unknown.
  - Node transitions for approve, reject, and edit.
- Validation:
  - `pytest tests/text_to_sql_agent/agents/test_human_approval_agent.py -v` -> 9 passed.
  - `pytest tests/text_to_sql_agent/graphs/test_query_graph.py -v` -> 12 passed.
  - `ruff check` on modified files -> all checks passed.

### T-2026-05-18-045 - Implement SQL security guard agent

- Created `src/text_to_sql_agent/agents/security_guard_agent.py`:
  - Added `validate_sql_security(sql)` deterministic security checks for MVP read-only execution.
  - Security rules: read-only statement entrypoint (`SELECT`/`WITH`), blocked DML/DDL operations (`INSERT`, `UPDATE`, `DELETE`, `DROP`, etc.), suspicious pattern detection (`--`, `/*`, `UNION SELECT`, `OR 1=1`).
  - Added `SQLSecurityValidationResult` structured output (`approved`, `violations`).
  - Added `build_security_guard_node()` LangGraph adapter that validates `edited_sql` (if present) or `generated_sql`.
- Updated `src/text_to_sql_agent/graphs/query_graph.py`:
  - Replaced security guard stub with `node_security_guard = build_security_guard_node()`.
- Updated `src/text_to_sql_agent/agents/__init__.py` exports:
  - Added `build_security_guard_node` and `validate_sql_security`.
- Added tests `tests/text_to_sql_agent/agents/test_security_guard_agent.py` (11 cases):
  - Approval for safe read-only queries.
  - Rejections for non-read-only entrypoint, blocked operations, and suspicious patterns.
  - Node behavior for success, edited SQL precedence, and failure path.
- Validation:
  - `pytest tests/text_to_sql_agent/agents/test_security_guard_agent.py -v` -> 11 passed.
  - `pytest tests/text_to_sql_agent/graphs/test_query_graph.py -v` -> 12 passed.
  - `ruff check` on modified files -> all checks passed.

### T-2026-05-18-044 - Implement SQL syntax validator agent

- Created `src/text_to_sql_agent/agents/syntax_validator_agent.py`:
  - Added `validate_sql_syntax(sql)` deterministic validation for MVP read-only policy.
  - Validation rules: non-empty SQL, single statement, starts with `SELECT`/`WITH`, no disallowed write/DDL operations, balanced parentheses, balanced single quotes.
  - Added `SQLSyntaxValidationResult` structured output (`valid`, `errors`).
  - Added `build_syntax_validator_node()` LangGraph adapter that validates `edited_sql` (if present) or `generated_sql`.
- Updated `src/text_to_sql_agent/graphs/query_graph.py`:
  - Replaced syntax validator stub with `node_syntax_validator = build_syntax_validator_node()`.
- Updated `src/text_to_sql_agent/agents/__init__.py` exports:
  - Added `build_syntax_validator_node` and `validate_sql_syntax`.
- Added tests `tests/text_to_sql_agent/agents/test_syntax_validator_agent.py` (10 cases):
  - Valid SELECT and WITH CTE SQL.
  - Invalid SQL cases: empty SQL, multiple statements, disallowed operations, unbalanced parentheses, unbalanced quotes.
  - Node behavior for success, edited SQL precedence, and failure path.
- Validation:
  - `pytest tests/text_to_sql_agent/agents/test_syntax_validator_agent.py -v` -> 10 passed.
  - `pytest tests/text_to_sql_agent/graphs/test_query_graph.py -v` -> 12 passed.
  - `ruff check` on modified files -> all checks passed.

### T-2026-05-18-043 - Implement SQL generator agent

- Created `src/text_to_sql_agent/agents/sql_generator_agent.py`:
  - `generate_read_only_sql(user_question, schema_context, dialect, max_limit)` with deterministic read-only SQL generation.
  - `SQLGenerationResult` structured output (`sql`, `rationale`, `table_used`, `intent`).
  - Intent detection for MVP (`count` vs `list`) based on user question tokens.
  - Schema parser for `TABLE ...` / column lines from formatted schema context.
  - Identifier safety checks and SQL quoting for SQLite/PostgreSQL.
  - Safe fallback query (`SELECT 1 AS result LIMIT 1`) when schema tables are unavailable.
- Added LangGraph adapter `build_sql_generator_node(max_limit=100)`:
  - Produces `generated_sql`, `sql_rationale`, `status=validating`, and structured log messages.
  - Returns `status=failed` + `error_message` on generation errors.
- Updated `src/text_to_sql_agent/graphs/query_graph.py`:
  - Replaced SQL generator stub node with `node_sql_generator = build_sql_generator_node()`.
- Updated `src/text_to_sql_agent/agents/__init__.py` exports:
  - Added `generate_read_only_sql` and `build_sql_generator_node`.
- Added tests `tests/text_to_sql_agent/agents/test_sql_generator_agent.py` (7 cases):
  - Count intent, list intent with limit, table selection fallback, no-table probe query, invalid limit, node success path, node failure path.
- Validation:
  - `pytest tests/text_to_sql_agent/agents/test_sql_generator_agent.py -v` -> 7 passed.
  - `pytest tests/text_to_sql_agent/graphs/test_query_graph.py -v` -> 12 passed.
  - `ruff check` on modified files -> all checks passed.

### T-2026-05-18-042 - Implement schema context agent

- Created `src/text_to_sql_agent/agents/schema_context_agent.py`:
  - `format_schema_context(schema, table_filter)` — formats `DatabaseSchema` into a compact multi-line text block with `-- Database: id (dialect)` header and `TABLE / col type [PK/FK/NOT NULL]` body. Optional `table_filter` restricts output; stopwords and punctuation stripped automatically.
  - `build_schema_context(database_id, connection_config, dialect, table_filter)` — calls `get_introspection_provider`, introspects, normalizes via `normalize_raw_schema`, and formats.
  - `build_schema_context_node(connection_config)` — returns a LangGraph-compatible node function `(state: dict) -> dict` that populates `schema_context`, `status`, and `log_messages` on success, or `status=failed` / `error_message` on any exception.
- Updated `src/text_to_sql_agent/agents/__init__.py`: exported `build_schema_context`, `build_schema_context_node`, `format_schema_context`.
- Updated `src/text_to_sql_agent/graphs/query_graph.py`:
  - Replaced stub `node_schema_context` function with module-level `node_schema_context = build_schema_context_node(_DEFAULT_CONNECTION_CONFIG)`.
  - Extended `build_query_graph(checkpointer, connection_config)` signature so callers can inject real connection parameters; when `connection_config` is provided a fresh node is built, otherwise the default empty-config stub is used (safe for tests).
- Tests: 13 passed — `TestFormatSchemaContext` (10 cases), `TestBuildSchemaContext` (1 case, mocked provider), `TestBuildSchemaContextNode` (2 cases: success and failure).
- Existing `test_query_graph.py` 12 tests still pass (default stub path, no real DB required).
- Validation: `ruff check` passes for all modified files.

### T-2026-05-18-041 - Implement orchestration graph for DB agents

- Designed `QueryState` TypedDict (`graphs/query_state.py`) with fields for:
  - Session context: `user_id`, `conversation_id`, `message_id`.
  - Input: `user_question`, `database_id`, `dialect`.
  - Each pipeline step: schema context, generated SQL, syntax/security results, human approval, execution result, analytics chart, export path, insight text.
  - Control flow (`status`) and observability (`log_messages` with LangGraph append reducer).
- Built `build_query_graph()` (`graphs/query_graph.py`) with stub nodes for all steps:
  - `schema_context` → `sql_generator` → `syntax_validator` → `security_guard` → `human_approval` (interrupt) → `query_executor` → `analytics` → `export` → `done`.
  - `failed` terminal node reachable from syntax, security, approval, and execution failures.
  - Conditional routing after each validation/decision node.
  - `interrupt_before=["human_approval"]` ensures the graph pauses for explicit user confirmation before any SQL execution.
  - Checkpointer defaults to `MemorySaver` for development; injectable for production.
- Exported `QueryState` and `build_query_graph` from `graphs/__init__.py`.
- Tests: 12 passed — node unit tests (syntax validator, security guard) and graph integration tests (happy path, approve, reject, edit, log accumulation).
- Validation: `ruff check` passes for both new files.


- Defined scope: stable user identifier, per-user conversation isolation, ordered message history, future-ready for persistent backend.
- Delivered `src/text_to_sql_agent/models/session.py`:
  - `User` — stable `user_id`, `display_name`, optional `email`, `is_active`, UTC `created_at`.
  - `Conversation` — `conversation_id`, `user_id`, optional `title`, UTC timestamps, `metadata` dict for db/dialect context.
  - `ChatMessage` — `message_id`, `conversation_id`, `MessageRole` enum (user/assistant/system/tool), `content`, UTC `created_at`, `metadata` for SQL/approval context.
- Delivered `src/text_to_sql_agent/repositories/session_repository.py`:
  - Abstract `SessionRepository` with `save_user`, `get_user`, `save_conversation`, `get_conversation`, `list_conversations`, `append_message`, `list_messages`.
  - `InMemorySessionRepository`: volatile in-memory implementation for development and tests; designed for drop-in replacement with a DB-backed implementation.
- Exported all new symbols from `models/__init__.py` and `repositories/__init__.py`.
- Tests: 17 model tests + 11 repository tests = 28 passed, 0 failed.
- Validation: `ruff check` passes for both new files.

### T-2026-05-18-039 - Harden schema shortcut parsing

- Investigated why `view schema for table optins?` was being interpreted as `table, optins?`.
- Root cause analysis:
  - The manual schema shortcut branch in `main_terminal.py` split the suffix literally and kept filler words and punctuation.
  - That caused exact-name lookup to fail even though `optins` exists.
- Implemented fix:
  - Added `_extract_schema_table_names()` to drop filler words such as `table`, `tables`, `for`, `the`, and `and`.
  - Stripped trailing punctuation before calling `get_db_schema()`.
- Validation:
  - Smoke checks now parse `table optins?` as `['optins']`.
  - `ruff check main_terminal.py` passes.

### T-2026-05-18-038 - Fix terminal agent tool invocation and deprecation path

- Reproduced terminal runtime issue in `main_terminal.py`:
  - Deprecation warning from `langgraph.prebuilt.create_react_agent` migration path.
  - Runtime failure: `Too many arguments to single-input tool get_schema`.
- Root cause analysis:
  - Agent constructor path was using a deprecated import for the installed LangChain/LangGraph version.
  - `get_schema` was defined as legacy single-input `Tool`, which conflicted with agent tool-call argument shape.
- Implemented fix:
  - Migrated agent construction to `langchain.agents.create_agent`.
  - Replaced `Tool` with `StructuredTool` definitions for both `get_schema` and `execute_query`.
  - Added `_get_schema_tool_input(table_names: str = "")` adapter to support optional table filtering without argument-shape errors.
- Validation:
  - `ruff check main_terminal.py` passes.
  - Module import and schema-tool invocation smoke checks pass.

### T-2026-05-18-037 - Implement secret placeholder resolution for environment config

- Identified placeholder-based secret markers (`[LOAD_FROM_SECRETS]`) in production environment configuration.
- Registered a planned task to implement runtime resolution of secret placeholders into actual values via a dedicated secrets-loading mechanism.
- Scope includes configuration-layer integration and explicit fallback behavior for local and test environments.
- Agreed proposal for implementation:
  - Source priority: process environment variables -> secrets backend -> `.env*` values.
  - Production backend: AWS Secrets Manager (`SECRETS_BACKEND=aws_secrets_manager`).
  - Local/test backend: file-based secret provider (non-committed local secret file).
  - Placeholder policy: resolve exact token `[LOAD_FROM_SECRETS]` only.
  - Failure policy: fail fast in production for unresolved required placeholders; emit warnings in local/test for optional values.
  - Verification: add unit tests for resolver precedence and unresolved-placeholder behavior, plus local smoke test with file backend.
- Implementation started (`in_progress`):
  - Added `src/text_to_sql_agent/config/secrets.py` with placeholder resolver and provider abstractions.
  - Added `FileSecretsProvider` (JSON file backend) and `AwsSecretsManagerProvider` (JSON secret payload backend).
  - Added `resolve_secret_placeholders()` with source priority and environment-specific unresolved-placeholder policy.
  - Exported resolver utilities via `src/text_to_sql_agent/config/__init__.py`.
  - Added focused tests in `tests/text_to_sql_agent/config/test_secrets.py` for precedence, prod fail-fast, dev warnings, and file backend behavior.
- Runtime integration completed:
  - Added `src/text_to_sql_agent/config/settings.py` with `load_runtime_environment()` to merge `.env` + environment-specific files (`.env.dev/.env.test/.env.prod`), resolve placeholders, and populate runtime environment.
  - Integrated runtime loader into `main_terminal.py` startup so secret placeholder resolution executes in the real run path.
  - Added integration tests in `tests/text_to_sql_agent/config/test_settings_runtime.py` for runtime loading behavior and environment-file selection.
  - Validation executed: `ruff check` for touched config/runtime files and targeted pytest suite for config tests.
  - Task status moved to `done`.

### T-2026-05-18-036 - Refactor terminal prototype into project architecture

**Code review findings (initial analysis):**
- `main_terminal.py` had hardcoded `DB_PATH = "database.db"`, raw f-string PRAGMA calls (`PRAGMA table_info({table_name})`), arbitrary SQL execution without read-only enforcement, and no use of any established project layer.

**Implementation:**
- Replaced raw SQLite introspection with `SQLiteIntrospectionProvider.introspect()` + `normalize_raw_schema()` — canonical project path for schema access.
- DB path now read from `SQLITE_PATH` env var (with `database.db` fallback for ad-hoc use).
- `get_db_schema(table_filter)` accepts an optional list of table names, enabling `schema users orders` style commands from the terminal.
- Read-only SQL enforcement: `query_database()` rejects any input not starting with `SELECT`, `EXPLAIN`, or `WITH` before touching the database.
- Loguru integrated at `WARNING` level on stderr so terminal output stays clean.
- Agent executor is now lazily initialised on the first natural-language query — `schema` commands work without `OPENAI_API_KEY`.
- Migrated agent wiring from removed LangChain v0 API (`AgentExecutor`) to the current LangGraph API (`langgraph.prebuilt.create_react_agent`).
- Added environment key alias support in terminal agent startup: `OPENAI_API_KEY`, `OPENAI_KEY`, `OPENAI_TOKEN`.
- Added natural-language schema shortcuts (`view full database schema`, `show schema for ...`) that bypass LLM initialization and directly call schema inspection.
- Removed `show_graph` tool (no real implementation) and the `graph` shortcut.
- `ruff check` passes; AST-level parse confirmed valid.

### T-2026-05-15-035 - Implement SchemaReaderAgent entrypoint

- Added `src/text_to_sql_agent/agents/schema_reader_agent.py` with a thin `SchemaReaderAgent` wrapper.
  - `build_initial_schema_read_state()` maps `SchemaRefreshRequest` into the full `SchemaReadState` shape expected by the graph.
  - `SchemaReaderAgent.run()` accepts a request plus `connection_config_ref`, builds the initial state, and invokes the compiled schema ingestion graph.
  - The agent supports explicit request ID overrides and a deterministic default request ID factory.
- Updated `src/text_to_sql_agent/agents/__init__.py` to export the new entrypoint helpers.
- Replaced the agents scaffold test with targeted tests that verify state construction and graph invocation behavior.

### T-2026-05-15-034 - Assemble LangGraph schema ingestion graph and edges

- Added `src/text_to_sql_agent/graphs/schema_graph.py` with a compiled `StateGraph` for schema ingestion.
  - The graph sequences `load_connection_context` -> `introspect_schema` -> `normalize_schema` -> `build_schema_documents` -> `persist_schema_snapshot` -> `index_schema_embeddings` -> completion.
  - Conditional edges now route failed nodes through retry or terminal failure handling, and successful runs end in a done state with `completed_at` set.
  - The graph builder accepts injected connection resolution, provider, snapshot, vector store, and embedder dependencies so tests can run deterministically.
- Updated `src/text_to_sql_agent/graphs/__init__.py` to export `build_schema_ingestion_graph`.
- Replaced the graphs scaffold test with concrete graph workflow tests covering successful completion, one retry after transient introspection failure, and terminal failure when retries are exhausted.

## 2026-05-15

### T-2026-05-15-033 - Implement LangGraph schema ingestion graph nodes

- Created `src/text_to_sql_agent/graphs/schema_nodes.py` with explicit LangGraph node functions.
  - `load_connection_context()` validates connection references and resolves dialect metadata.
  - `introspect_schema()` resolves the provider and captures raw introspection results.
  - `normalize_schema()` converts raw introspection into canonical `DatabaseSchema` and stores it in state as `normalized_schema`.
  - `build_schema_documents()` derives stable document IDs from the normalized schema.
  - `persist_schema_snapshot()` saves the canonical schema snapshot and records `snapshot_id`.
  - `index_schema_embeddings()` builds documents, generates embeddings, and persists embedding records.
- Updated `src/text_to_sql_agent/graphs/state.py` to add the `normalized_schema` field for the canonical intermediate schema payload.
- Updated `src/text_to_sql_agent/graphs/__init__.py` to export the node functions.
- Added 6 tests in `tests/text_to_sql_agent/graphs/test_schema_nodes.py` covering each node and state transitions.
- Updated `tests/text_to_sql_agent/graphs/test_state.py` to account for the new `normalized_schema` field.
- All graph state and node tests pass.

### T-2026-05-15-032 - Implement schema indexing service

- Created `src/text_to_sql_agent/services/schema_indexing.py` with `index_schema_embeddings()`.
  - Accepts `list[SchemaDocument]`, a `VectorStoreRepository`, and an injected embedder callable.
  - Builds `SchemaEmbeddingRecord` entries with deterministic or injected embedding IDs.
  - Uses timezone-aware indexing timestamps and short-circuits on empty input.
  - Returns the embedding IDs produced by the vector store repository.
- Updated `src/text_to_sql_agent/services/__init__.py` to export `index_schema_embeddings`.
- Added 5 tests in `tests/text_to_sql_agent/services/test_schema_indexing.py` covering return values, record materialization, embedder invocation count, default embedding IDs, and empty-input handling.
- All 5 indexing tests pass.

### T-2026-05-15-031 - Define abstract vector store repository interface

- Created `src/text_to_sql_agent/repositories/vector_store_repository.py` with abstract `VectorStoreRepository` contract.
  - Defines `upsert_documents(records)` for embedded schema records.
  - Defines `search_similar(query_vector, limit, database_id, snapshot_id)` for vector search with optional filtering.
  - Defines `delete_by_snapshot(snapshot_id)` for snapshot-scoped cleanup.
- Updated `src/text_to_sql_agent/repositories/__init__.py` to export `VectorStoreRepository`.
- Added 7 tests in `tests/text_to_sql_agent/repositories/test_vector_store_repository.py` covering abstract instantiation, incomplete subclasses, upsert return values, search filtering, search limits, delete counts, and empty-result behavior.
- All 7 vector store contract tests pass.

### T-2026-05-15-030 - Implement schema document building service

- Created `src/text_to_sql_agent/services/schema_document_builder.py` with `build_schema_documents()`.
  - Builds `SchemaDocument` records for `table`, `column_group`, and `relationship` granularity.
  - Produces deterministic document IDs from snapshot, table, granularity, and relationship columns.
  - Orders columns by `ordinal_position` for stable content and column lists.
  - Generates readable content strings that summarize table metadata, columns, and foreign-key relationships.
  - Carries domain tags and basic metadata into each document.
- Updated `src/text_to_sql_agent/services/__init__.py` to export `build_schema_documents`.
- Added 5 tests in `tests/text_to_sql_agent/services/test_schema_document_builder.py` covering document types, deterministic IDs, readable content, metadata propagation, and column ordering.
- All 5 builder tests pass.

### T-2026-05-15-029 - Implement schema snapshot repository

- Created `src/text_to_sql_agent/repositories/schema_snapshot_repository.py` with a file-based `SchemaSnapshotRepository`.
  - Persists each `DatabaseSchema` snapshot as a JSON file named by `snapshot_id`.
  - Stores both the canonical schema payload and a `SchemaSnapshotRef` summary in the same file.
  - Supports `save()`, `load()`, `list()`, and `delete()` operations.
  - Creates the storage directory on initialization.
- Updated `src/text_to_sql_agent/repositories/__init__.py` to export `SchemaSnapshotRepository`.
- Added 9 tests in `tests/text_to_sql_agent/repositories/test_schema_snapshot_repository.py` covering save/load round-trip, list filtering, delete behavior, missing snapshot errors, and storage directory creation.
- All 9 repository snapshot tests pass.

### T-2026-05-15-028 - Implement schema normalization service

- Created `src/text_to_sql_agent/services/schema_normalization.py` with `normalize_raw_schema()` and `build_snapshot_id()`.
  - Converts `RawIntrospectionResult` into canonical `DatabaseSchema`.
  - Generates stable, filesystem-friendly snapshot IDs from `database_id` and `introspected_at`.
  - Normalizes table types such as `BASE TABLE` to `TABLE`.
  - Normalizes common PostgreSQL and SQLite data-type aliases into stable canonical types.
  - Resolves primary key ordering from column metadata and marks foreign-key columns from table relationships.
  - Deduplicates repeated foreign-key relationships before building canonical schema entries.
- Added `src/text_to_sql_agent/services/__init__.py` to export service-layer normalization helpers.
- Added 8 tests in `tests/text_to_sql_agent/services/test_schema_normalization.py` covering snapshot IDs, explicit snapshot override, table metadata mapping, PK/FK resolution, foreign-key deduplication, PostgreSQL type normalization, SQLite affinity normalization, and timestamp/version preservation.
- All 8 normalization tests pass.

### T-2026-05-15-027 - Implement introspection provider factory and registry

- Created `src/text_to_sql_agent/repositories/provider_factory.py` with a registry of supported introspection providers.
  - Added `PROVIDER_REGISTRY` mapping normalized dialect keys to provider classes.
  - Added `normalize_dialect()` to resolve aliases such as `postgres` -> `postgresql` and `sqlite3` -> `sqlite`.
  - Added `get_introspection_provider()` to return a fresh provider instance for the requested dialect.
  - Raises a helpful `ValueError` that includes supported dialects for unknown inputs.
- Updated `src/text_to_sql_agent/repositories/__init__.py` to export the factory, registry, and normalization helper.
- Added 11 tests in `tests/text_to_sql_agent/repositories/test_provider_factory.py` covering registry contents, alias normalization, case-insensitive lookup, fresh instance creation, and unsupported dialect errors.
- All 11 factory tests pass; total repository tests now 55.

### T-2026-05-15-026 - Implement PostgreSQL schema introspection adapter

- Created `src/text_to_sql_agent/repositories/postgresql_provider.py` with concrete `PostgresIntrospectionProvider` class.
  - Implements `introspect(database_id, connection_config)` for PostgreSQL databases.
  - Reads tables and views from `information_schema.tables` with system schema filtering.
  - Reads column metadata via `information_schema.columns` with nullability, defaults, numeric/character constraints.
  - Extracts primary and unique constraints via `key_column_usage` + `table_constraints`.
  - Reads foreign keys via multi-table join with cascade rule extraction.
  - Reads indexes from `pg_indexes` with uniqueness detection and column name parsing.
- Updated `src/text_to_sql_agent/repositories/__init__.py` to export `PostgresIntrospectionProvider`.
- Added `psycopg2-binary==2.9.12` to project dependencies.
- Created 17 comprehensive tests covering connection validation, error handling, schema discovery, constraint extraction, and connection cleanup.
- All 17 tests pass; total repository tests now 44 after this task.

### T-2026-05-15-025 - Implement SQLite schema introspection adapter

- Created `src/text_to_sql_agent/repositories/sqlite_provider.py` with concrete `SQLiteIntrospectionProvider` class.
  - Implements `introspect(database_id, connection_config)` for SQLite databases.
  - Reads tables and views from `sqlite_master`.
  - Reads column metadata via `PRAGMA table_info` with proper nullability handling (PK columns implicitly NOT NULL).
  - Reads foreign keys via `PRAGMA foreign_key_list` with ON DELETE/UPDATE rules.
  - Reads indexes via `PRAGMA index_list` and `PRAGMA index_info`.
  - Handles default values and data types.
- Updated `src/text_to_sql_agent/repositories/__init__.py` to export `SQLiteIntrospectionProvider`.
- Added 14 tests in `tests/text_to_sql_agent/repositories/test_sqlite_provider.py` covering basic introspection, table discovery, column nullability, primary keys, foreign keys, indexes, default values, error handling (missing path, invalid path), in-memory databases, multiple databases, timestamp recording, and empty database handling.
- All 14 tests pass.

### T-2026-05-15-024 - Define abstract schema introspection provider interface

- Created `src/text_to_sql_agent/repositories/introspection_provider.py` with abstract base class `SchemaIntrospectionProvider`.
  - Single abstract method: `introspect(database_id, connection_config) -> RawIntrospectionResult`.
  - Comprehensive docstring with expected connection_config keys (host, port, database, username, password, extra_params).
  - Defines contract for all dialect-specific introspection implementations.
- Created `src/text_to_sql_agent/repositories/__init__.py` exporting `SchemaIntrospectionProvider`.
- Added 12 tests in `tests/text_to_sql_agent/repositories/test_introspection_provider.py` covering abstract class instantiation errors, concrete implementations, validation logic, return type checking, and multi-provider independence.
- All 12 tests pass.

### T-2026-05-15-023 - Define SchemaReadState TypedDict for LangGraph

- Created `src/text_to_sql_agent/graphs/state.py` with `SchemaReadState` as a `TypedDict` with `Annotated` fields for LangGraph workflow.
  - State tracks identity (request_id, database_id, dialect), request params (refresh_mode, target_tables, force_refresh), runtime context (connection_config_ref), step outputs (references only: introspection_result, snapshot_id, document_ids, embedding_ids), control flow (status, current_node, retry_count), and observability (errors, warnings, timestamps).
  - Uses `Annotated[list[str], add_messages]` for error and warning lists to enable LangGraph message reducers.
- Created `src/text_to_sql_agent/graphs/__init__.py` exporting `SchemaReadState`.
- Added 18 tests in `tests/text_to_sql_agent/graphs/test_state.py` covering TypedDict structure, state initialization, partial updates, status transitions, error/warning accumulation, refresh modes, target tables filtering, connection config references, timestamp tracking, and full workflow simulations (success and failure paths).
- All 18 tests pass.

### T-2026-05-15-022 - Define lifecycle and operational Pydantic models

- Created `src/text_to_sql_agent/models/lifecycle.py` with two Pydantic `BaseModel` classes: `SchemaSnapshotRef`, `SchemaRefreshRequest`.
  - `SchemaSnapshotRef` tracks the lifecycle of a saved schema snapshot: snapshot_id, database_id, dialect, created_at, table_count, status (fresh, stale, indexing, indexed, failed).
  - `SchemaRefreshRequest` specifies schema refresh parameters: database_id, refresh_mode (full, incremental, metadata_only), optional target_tables, and force flag.
- Updated `src/text_to_sql_agent/models/__init__.py` to export both new models.
- Added 17 tests in `tests/text_to_sql_agent/models/test_lifecycle.py` covering required fields, optional defaults, edge cases (zero tables, 10k tables, empty/many target tables), status values, refresh modes, None vs empty list distinction, serialization roundtrip, and request-snapshot workflow consistency.
- All 17 tests pass.

### T-2026-05-15-021 - Define document and embedding Pydantic models

- Created `src/text_to_sql_agent/models/document.py` with two Pydantic `BaseModel` classes: `SchemaDocument`, `SchemaEmbeddingRecord`.
  - `SchemaDocument` represents a semantic document chunk for vector indexing with granularity (table, column_group, relationship), human-readable content, domain tags, and metadata.
  - `SchemaEmbeddingRecord` represents a computed embedding vector linked to a document and snapshot.
- Updated `src/text_to_sql_agent/models/__init__.py` to export both new models.
- Added 13 tests in `tests/text_to_sql_agent/models/test_document.py` covering required fields, optional defaults, validation errors, edge cases (empty vectors, zero vectors, large vectors), serialization roundtrip, datetime precision, and document-embedding pair consistency.
- All 13 tests pass.

### T-2026-05-15-020 - Define canonical schema Pydantic models

- Created `src/text_to_sql_agent/models/schema.py` with four Pydantic `BaseModel` classes: `ForeignKeySchema`, `ColumnSchema`, `TableSchema`, `DatabaseSchema`.
- Updated `src/text_to_sql_agent/models/__init__.py` to export all four canonical models alongside existing raw introspection models.
- Added 12 tests in `tests/text_to_sql_agent/models/test_schema.py` covering required fields, optional defaults, missing-field validation errors, nested composition, and serialization roundtrip.
- All 12 tests pass.

### T-2026-05-15-019 - Define raw introspection Pydantic models

- Created `src/text_to_sql_agent/models/introspection.py` with five Pydantic `BaseModel` classes: `RawColumnMeta`, `RawForeignKeyMeta`, `RawIndexMeta`, `RawTableMeta`, `RawIntrospectionResult`.
- Created `src/text_to_sql_agent/models/__init__.py` exporting all five models.
- Added 13 tests in `tests/text_to_sql_agent/models/test_introspection.py` covering required fields, optional defaults, missing-field validation errors, and serialization roundtrip via `model_dump` / `model_validate`.
- All 13 tests pass.

### T-2026-05-15-018 - Point test SQLite settings to repository database

- Updated `.env.test` so `SQLITE_PATH` points to `tests/text_to_sql_agent/db/test_database.db`.
- Replaced the config scaffold test with a check that the test environment references the repository-backed SQLite file.
- Kept the SQLite test database path deterministic and local to the repository.

## 2026-05-12

### T-2026-05-12-017 - Mirror tests package layout with src

- Created mirrored test directories for all source packages under `tests/text_to_sql_agent/`:
   - `agents`, `config`, `graphs`, `models`, `prompts`, `repositories`, `services`, `utils`
- Added `.gitkeep` files to preserve empty test package directories in version control.
- Added `tests/text_to_sql_agent/README.md` with explicit test placement mapping rules.
- Updated `.github/copilot-instructions.md` to require mirrored test layout for future tests.
- Updated `.tester.instructions.md` test structure and command examples to the mirrored layout.
- Updated `docs/AGENTS.md` to include mirrored layout responsibility for the Tester/QA agent.

## 2026-05-11

### T-2026-05-11-016 - Define prompt metrics and evaluation gates

- Added typed evaluation gate contract in `src/text_to_sql_agent/prompts/evaluation_gates.py`.
- Defined default gate profile (`default-v1`) with hard-fail thresholds for `validity_rate`, `execution_success_rate`, `policy_violation_rate`, and `leakage_rate`.
- Added deterministic gate evaluation function returning blocking violations and warnings.
- Added sample-size warning behavior with configurable `minimum_samples`.
- Added `docs/PROMPT_EVALUATION_GATES.md` as the metrics and gate reference.
- Added `tests/test_prompt_evaluation_gates.py` to validate pass/fail behavior and profile validation constraints.

### T-2026-05-11-015 - Design prompt storage and version registry

- Added typed storage and registry contract in `src/text_to_sql_agent/prompts/storage_registry.py`.
- Defined external storage configuration model (`backend`, `bucket_or_container`, `namespace`, `object_key_prefix`, `region`).
- Defined version record contract with status lifecycle, checksum validation, template URI validation, and ownership metadata.
- Defined registry pointer validation for `latest_version`, `active_version`, and `canary_version` consistency.
- Added `docs/PROMPT_STORAGE_VERSION_REGISTRY.md` with storage approach and versioning rules.
- Added `tests/test_prompt_storage_registry.py` to validate registry boundaries and pointer integrity.

### T-2026-05-11-014 - Define user override policy and validation boundaries

- Added typed user override policy contract in `src/text_to_sql_agent/prompts/override_policy.py`.
- Defined explicit customizable sections (`style_instructions`, `business_glossary`, `few_shot_examples`, `response_format_hint`, `domain_filters`).
- Defined immutable safety and governance sections (`safety_guardrails`, `required_placeholders`, `disallowed_operations`, `read_only_enforcement`, `tenant_isolation`, `approval_workflow`).
- Implemented validation boundaries for section membership, immutable enforcement, payload size limits, and rationale requirements.
- Added `docs/PROMPT_USER_OVERRIDE_POLICY.md` as the policy reference.
- Added `tests/test_prompt_override_policy.py` to validate override boundary behavior.

### T-2026-05-11-013 - Create change request process for prompt updates

- Added typed change request contract in `src/text_to_sql_agent/prompts/change_request.py`.
- Defined required fields for all prompt updates, including version increment and mandatory rationale, risk, test evidence, and rollback plan.
- Implemented standard approval gate validation requiring `prompt-owner`, `data-platform`, and `security` roles before approved/implemented/closed states.
- Implemented emergency hotfix path with required incident id, expedited approvals, and postmortem deadline/completion checks.
- Added `docs/PROMPT_CHANGE_REQUEST_PROCESS.md` with required fields, review flow, approvers, and emergency hotfix guidance.
- Added `tests/test_prompt_change_request.py` to validate governance constraints and hotfix behavior.

### T-2026-05-11-012 - Prepare enterprise prompt manifest contract

- Extended `src/text_to_sql_agent/prompts/prompt_manifest.py` with enterprise governance models:
   - `TenantIsolationPolicy`
   - `PromptAuditMetadata`
   - `PromptApprovalMetadata`
   - `PromptManifestEnterprise`
- Added `build_enterprise_manifest()` builder while preserving MVP contract compatibility.
- Implemented enterprise validation rules for tenant isolation modes, audit timestamp consistency, approval metadata integrity, and policy-level rollout constraints.
- Added `tests/test_prompt_manifest_enterprise.py` to validate enterprise contract behavior and failure modes.
- Added `docs/PROMPT_MANIFEST_ENTERPRISE.md` as the enterprise contract reference and linked it from the MVP document.

### T-2026-05-11-011 - Prepare MVP prompt manifest contract

- Added a typed MVP manifest contract in `src/text_to_sql_agent/prompts/prompt_manifest.py` using Pydantic validation.
- Defined minimal required fields for safe read-only SQL generation: identity, versioning, dialect, owner, template placeholders, read-only enforcement, guardrails, and deny-list operations.
- Added basic rollout control contract (`off`, `canary`, `full`) with strict percentage validation and active-status rollout requirements.
- Added `docs/PROMPT_MANIFEST_MVP.md` as the human-readable contract reference.
- Added `tests/test_prompt_manifest.py` to validate contract rules and failure modes.
- Updated `src/text_to_sql_agent/prompts/__init__.py` exports for manifest contract reuse.

### T-2026-05-11-010 - Audit SQL dialect differences and prompt scope

- Created `docs/SQL_DIALECT_SCOPE.md` with a concise comparison matrix for PostgreSQL, MySQL, Athena, and SQLite focused on prompt-relevant SQL differences.
- Added dialect-specific prompt scope rules and few-shot example selection guidance.
- Implemented a typed prompt-scope contract in `src/text_to_sql_agent/prompts/dialect_scope.py` to keep dialect constraints reusable in code.
- Added `tests/test_dialect_scope.py` to validate matrix completeness, read-only example constraints, and dialect lookup behavior.
- Updated `docs/ARCHITECTURE.md` to reference dialect scope governance and its test boundary.

### T-2026-05-11-001 - Create project working instructions

- Created `.github/copilot-instructions.md` for the repository.
- Added project-specific guidance for scope, structure, implementation rules, validation, testing, and secrets handling.
- Added an explicit rule that all documentation, comments, and technical explanations must be written in English regardless of the user's language.
- Established `docs/TASKS.md` as the primary task registry.
- Established `docs/WORKLOG.md` and `docs/DECISIONS.md` as supporting project history files.

### T-2026-05-11-002 - Create project changelog

- Created `docs/CHANGELOG.md` as the project-level record of notable changes.
- Added the initial changelog entries for the documentation and process setup completed on 2026-05-11.
- Updated task tracking usage so changelog updates are expected when work changes project behavior, structure, process, or documentation expectations.
- Updated repository instructions so future work records notable changes in `docs/CHANGELOG.md`.

### T-2026-05-11-003 - Move changelog into docs

- Moved the changelog file from the repository root to `docs/CHANGELOG.md`.
- Updated task tracking instructions to use the changelog path inside `docs/`.
- Updated repository instructions so future sessions use `docs/CHANGELOG.md` as the canonical changelog location.
- Updated project history to reflect the new changelog location.

### T-2026-05-11-004 - Create initial architecture document

- Added `docs/ARCHITECTURE.md` as the living reference for the repository architecture.
- Documented the target system shape because the package layout exists but the implementation has not been built yet.
- Described the intended responsibilities of `agents`, `graphs`, `services`, `repositories`, `models`, `prompts`, `config`, and `utils`.
- Added a high-level request lifecycle from natural language input to SQL generation, execution, and response formatting.
- Updated repository instructions to keep `docs/ARCHITECTURE.md` aligned with future architectural changes.

### T-2026-05-11-005 - Configure environment and package management

- Created `.vscode/settings.json` to configure VS Code to use `venvtext2sql/bin/python` as the default Python interpreter.
- Updated `.github/copilot-instructions.md` with an explicit "Environment Setup" section documenting `venvtext2sql`, `uv`, and version pinning.
- Added a new "Dependency Management" section to the repository instructions stating that all dependency operations must use `uv`.
- Documented that `uv.lock` is the source of truth for pinned versions and must be committed alongside `pyproject.toml`.

### T-2026-05-11-006 - Show canonical venv in status bar

- Updated `.vscode/settings.json` to set `python.interpreter.infoVisibility` to `always`.
- Kept `venvtext2sql/bin/python` as the workspace default interpreter so the status bar consistently shows the canonical environment label.

### T-2026-05-11-009 - Set up specialized GitHub Copilot agents

**Task completed.** Created 5 specialized GitHub Copilot agents for different project roles.

**Files Created:**
- `.architect.instructions.md`: Architecture design and system review agent
- `.taskmanager.instructions.md`: Task planning and project organization agent
- `.developer.instructions.md`: Code implementation and feature development agent
- `.tester.instructions.md`: Quality assurance and testing agent
- `.documentarian.instructions.md`: Documentation and technical writing agent
- `docs/AGENTS.md`: Comprehensive guide for using the agents

**Agent Specifications**

**1. Architect Agent** (`.architect.instructions.md`)
- **Responsibility**: Design, review, and improve system architecture
- **Scope**: Component design, dependency analysis, refactoring proposals
- **Output**: Architecture diagrams, design documents, decision rationale
- **Key Files**: ARCHITECTURE.md, DECISIONS.md
- **Constraint**: Design-only; no direct implementation

**2. Task Manager Agent** (`.taskmanager.instructions.md`)
- **Responsibility**: Create, plan, and track project tasks
- **Scope**: Task creation, breakdown, prioritization, progress tracking
- **Output**: Task entries in TASKS.md, effort estimates, dependencies
- **Key Files**: TASKS.md, WORKLOG.md
- **Constraint**: Task format (T-YYYY-MM-DD-NNN) must be followed

**3. Developer Agent** (`.developer.instructions.md`)
- **Responsibility**: Implement features and write production code
- **Scope**: Code implementation, new modules, refactoring, Git workflow
- **Output**: Python code with type hints, feature branches, proper commits
- **Key Files**: src/, pyproject.toml, uv.lock
- **Constraint**: Type hints mandatory, feature branches only, no direct main commits

**4. Tester/QA Agent** (`.tester.instructions.md`)
- **Responsibility**: Ensure code quality and write comprehensive tests
- **Scope**: Unit/integration tests, mocking, edge cases, coverage, linting
- **Output**: Test code, coverage reports, quality validation
- **Key Files**: tests/, pytest config
- **Constraint**: 80%+ coverage target, deterministic tests

**5. Documentarian Agent** (`.documentarian.instructions.md`)
- **Responsibility**: Document system, APIs, and maintain documentation quality
- **Scope**: ARCHITECTURE.md, DECISIONS.md, CHANGELOG.md, WORKLOG.md, README
- **Output**: Clear documentation, Mermaid diagrams, examples
- **Key Files**: docs/*, README.md
- **Constraint**: English only, Markdown format, no outdated information

**Workflow Integration**

Typical multi-agent workflow:
1. **Architect** designs feature
2. **Task Manager** breaks it into tasks
3. **Developer** implements from tasks
4. **Tester** validates implementation
5. **Documentarian** documents the work

Each agent has specific constraints and file responsibilities to ensure:
- No overlapping work
- Clear accountability
- Quality standards are met
- Documentation stays current

**Usage in VS Code**

Activate agents via Copilot Chat:
- Ask with agent reference: "@architect: Design..." 
- Or look for agent selector dropdown in Copilot Chat
- Each agent applies its specific instructions automatically

**Key Features**
- **Role-based constraints**: Each agent knows its boundaries
- **Shared project rules**: All inherit base rules from `.github/copilot-instructions.md`
- **Complementary expertise**: Agents work together in sequence
- **Clear responsibilities**: No overlapping scope
- **Type-hinted code**: Developer agent enforces type hints
- **High test coverage**: Tester agent targets 80%+ coverage
- **Architectural alignment**: All code follows Architect's design

**Documentation**
- Full guide in `docs/AGENTS.md`
- Example prompts for each agent
- Quick reference table
- Coordination patterns for multi-agent workflows

**Benefits**
- Faster task completion through specialized agents
- Better code quality (dedicated testing)
- Comprehensive documentation (dedicated writer)
- Consistent architecture (architect reviews)
- Proper planning (task manager breaks down work)
- Reduced context switching for users

**Task completed.** Implemented production-ready structured logging using loguru.

**Files Created:**
- `src/text_to_sql_agent/config/logging.py`: LoggingConfig model and setup_logging() function.
- `src/text_to_sql_agent/config/__init__.py`: Module exports for logging configuration.

**Implementation Details:**

**LoggingConfig (Pydantic Model)**
- `level`: Global log level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Default: INFO.
- `format`: Log format — text (readable, colored) or json (production). Default: text.
- `output`: Output destination — stdout, file, or both. Default: stdout.
- `file_path`: Path to log file (required if output='file' or 'both').
- `retention_days`: Log file retention in days (auto-delete old logs). Default: 30.
- `rotation_size`: Log file rotation size (e.g., '100MB', '1GB'). Default: 100MB.

**Per-Module Log Levels**
- `level_agent`: Log level for agents module (default: DEBUG).
- `level_service`: Log level for services module (default: DEBUG).
- `level_repository`: Log level for repositories module (default: DEBUG).
- `level_graph`: Log level for graphs module (default: INFO).
- `level_model`: Log level for models module (default: INFO).
- `level_prompt`: Log level for prompts module (default: INFO).

**Functions**

1. `setup_logging(config: LoggingConfig) -> None`
   - Configures loguru based on LoggingConfig.
   - Removes default handler; adds configured handlers.
   - Supports both text (colored, readable) and JSON (production) formats.
   - Enables file rotation and gzip compression.
   - Validates that file_path is provided if file output is requested.
   - Raises ValueError if configuration is invalid.

2. `get_logger(name: str) -> logger`
   - Returns a configured loguru logger instance bound to a module name.
   - Usage: `from text_to_sql_agent.config import get_logger; log = get_logger(__name__)`

**Format Examples**

Text format (development):
```
DEBUG    | text_to_sql_agent.agents:query:45 | Processing SQL query validation
```

JSON format (production):
```
2026-05-11 14:23:15 | DEBUG    | text_to_sql_agent.agents:query:45 | Processing SQL query validation
```

**Usage in Code**

Simple usage:
```python
from text_to_sql_agent.config import get_logger

logger = get_logger(__name__)
logger.info("Starting agent initialization")
logger.debug("Config loaded from environment")
logger.error("Database connection failed", error=exc)
```

With context binding:
```python
logger.bind(request_id=request_id).info("Processing user request")
```

**Environment Configuration**

All .env files already contain loguru parameters:
- `.env`: Template with all logging keys.
- `.env.dev`: Text format, DEBUG level, stdout only, colored output.
- `.env.prod`: JSON format, INFO level, file output, gzip compression, 365-day retention.
- `.env.test`: WARNING level, stdout only, minimal overhead.

**Integration with .env Files**

Logging parameters in .env files (existing from T-2026-05-11-007):
```
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_OUTPUT=stdout
LOG_FILE=/var/log/text-to-sql-agent/app.log
LOG_LEVEL_AGENT=DEBUG
LOG_LEVEL_SERVICE=DEBUG
LOG_LEVEL_REPOSITORY=DEBUG
```

**Next Steps**
- Create `src/text_to_sql_agent/config/base.py` to load LoggingConfig from environment variables.
- Implement config loader in main.py to initialize logging on application startup.
- Add loguru to README under "Development Setup" section.

**Dependencies Added**
- `loguru==0.7.3` (added to pyproject.toml via uv).

**Task completed.** Implemented a comprehensive environment-based configuration system.

**Files Created:**
- `.env`: Template file with all 70+ configuration keys organized by category.
- `.env.dev`: Development environment (localhost, debug mode, test credentials, fast settings).
- `.env.prod`: Production environment (remote hosts, no debug, secrets placeholders, strict validation, high observability).
- `.env.test`: Testing/CI environment (in-memory DB, mocked LLM, disabled telemetry, fast execution).

**Configuration Categories Implemented:**

**1. Project Settings**
- Environment (dev/test/prod), debug/verbose flags, execution mode (sync/async).
- Request and query timeouts.

**2. Database Configuration (4 Drivers)**
- **SQLite**: File path, journal mode, timeout, foreign key support.
- **PostgreSQL**: Connection pooling (min/max size), SSL mode, credentials, timeouts.
- **Athena**: AWS region, S3 output, workgroup, catalog, schema (AWS-specific).
- **MySQL**: Pool size, charset (utf8mb4), SSL options, connection management.
- Common: Connection timeouts, query timeouts, retry logic, pool management (async/sync).

**3. LLM Configuration**
- Model name/version, API endpoint, API key, organization ID.
- Generation parameters (temperature, max_tokens, top_p, frequency/presence penalties).
- Request timeout, retry strategy (exponential backoff), retry delay.
- Rate limiting (requests/min, tokens/min), circuit breaker (threshold, timeout).
- Cost control (budget per day, cost estimation, token counting).
- Fallback model and model switching strategy (round_robin, least_cost, best_quality).

**4. Caching**
- Backend selection (memory, Redis).
- Redis config (host, port, password, DB, key prefix, TTL).
- In-memory cache (max size, eviction policy: LRU, LFU).

**5. Feature Flags**
- SQL validation, safety validators, experimental models.
- Audit logging, hot-reload config, request deduplication.

**6. Rate Limiting & Concurrency**
- Per-user, per-session, global limits with queue depth.

**7. SQL Validation**
- Injection prevention, complexity limits (max joins, subqueries).
- Complexity level (low/medium/high).

**8. Secrets Management**
- Backend selection: env files, AWS Secrets Manager, HashiCorp Vault.
- Credentials and endpoints for each backend.

**9. Observability & Telemetry**
- OpenTelemetry config (endpoint, batch size, export interval).
- Metrics export (Prometheus, DataDog, CloudWatch).
- Tracing (sample rate, enabled flag).

**10. Audit Logging**
- Audit log enabled, retention days, compression (gzip).
- Query history enabled, retention days.

**11. Database Migrations**
- Auto-migrate flag, strategy (safe/auto), rollback enabled.

**12. Request/Response Validation**
- Strict mode, schema version, error handling (reject/warn/ignore).

**13. Multi-Tenant Support**
- Enabled flag, isolation level (none/logical/full), context key.

**14. API Configuration**
- Port, host, CORS settings, origins.

**15. Monitoring & Health Checks**
- Health check interval, SLA thresholds (response time, success rate).
- Alerting endpoint.

**Additional Recommendations Added to WORKLOG:**
- **Rate limiting & circuit breaker**: Token bucket strategy, fallback on breach.
- **Caching layer**: Redis and in-memory support with TTL and eviction.
- **SQL validation rules**: Injection prevention, complexity limits.
- **Concurrent request limits**: Per user, per session, global queue.
- **Database migration management**: Schema versioning, auto-migrate, rollback.
- **API versioning support**: Version header requirement, deprecation.
- **Request/response schema validation**: Strict mode, error handling strategies.
- **Query execution history**: Audit logging with retention and compression.
- **Token counting & budget enforcement**: Per-request limits, daily budgets.
- **Model switching strategy**: Fallback, cost-aware, quality-based selection.
- **Monitoring & alerting**: Health checks, SLA thresholds, alerting.
- **Request deduplication**: Cache-within-window, idempotency key support.

**Environment Usage:**
- Development: `source .env.dev` (or use .env.dev for local testing).
- Production: Load from AWS Secrets Manager or Vault (never commit .env.prod).
- Testing: `.env.test` for CI/CD pipelines and automated tests.
- Template: `.env` for reference (all keys with documentation).

**Development Approach:**
- All `.env.dev`, `.env.test`, `.env` are compatible with production structure.
- `.env.prod` is not committed (marked in .gitignore).
- All sensitive values in `.env.prod` marked as `[LOAD_FROM_SECRETS]` for documentation.
- Development respects production patterns for safe transition to prod deployments.

**Git Protection:**
- Updated `.gitignore` to exclude `.env`, `.env.prod`, `.env.local`.
- Added `data/` and `logs/` directories to ignore list.
- Added IDE and OS files to ignore list (VS Code, IntelliJ, .DS_Store, etc.).
