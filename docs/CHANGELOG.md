# Changelog

All notable changes to this project will be documented in this file.

The format is intentionally simple and uses dated sections until versioned releases are introduced.


## 2026-06-08

### Planned

_None_

### Added

- Added README discoverability link for JetBrains venv setup checklist (T-2026-06-08-116):
  - Added a short Quick Setup note in `README.md` that links to `docs/JETBRAINS_VENV_CHECKLIST.md`.
  - Makes the checklist easier to find for new contributors during project onboarding.

- Added JetBrains venv activation checklist for project open workflow (T-2026-06-08-115):
  - Added `docs/JETBRAINS_VENV_CHECKLIST.md` with a minimal 3-step setup and verification list.
  - Covers interpreter selection (`venvtext2sql/bin/python`), terminal auto-activation shell path, and quick verification commands.

- Added persistent SQLite MCP executable configuration for local development (T-2026-06-08-114):
  - Installed `sqlite-mcp-server` in the canonical `venvtext2sql` environment.
  - Added `MCP_SQLITE_SERVER_CMD=venvtext2sql/bin/sqlite-mcp-server` to `.env.dev`.
  - Enabled `run_mcp_server_sqlite.sh` startup without manual environment-variable prefixing.


## 2026-06-05

### Planned

_None_

### Added

- Added convenience MCP server launch scripts (T-2026-06-05-113):
  - `run_mcp_server_sqlite.sh`
  - `run_mcp_server_postgresql.sh`
  - `run_mcp_server_athena.sh`
  - Documented the launchers in `README.md` and aligned them with the repository's MCP setup guidance.

- Added multi-dialect MCP query execution integration tests (T-2026-06-05-112):
  - New focused test coverage for SQLite, PostgreSQL, and Athena query execution via the MCP-backed factory.
  - Verified success payloads, read-only denial shapes, timeout propagation, and adapter-level error responses.

- Added MCP audit logging and observability for DB tools (T-2026-06-05-111):
  - Added `mcp_db_operation` event type in `src/text_to_sql_agent/models/trace.py`.
  - Added `make_mcp_db_audit_event()` in `src/text_to_sql_agent/services/audit_trail.py` for structured MCP DB operation event emission.
  - Updated `src/text_to_sql_agent/agents/query_execution_agent.py` to emit structured MCP audit events with request metadata, execution status, latency, and policy decision metadata.
  - Added/updated focused tests in `tests/text_to_sql_agent/models/test_trace.py`, `tests/text_to_sql_agent/services/test_audit_trail.py`, and `tests/text_to_sql_agent/agents/test_query_execution_agent.py`.
  - Updated `docs/ARCHITECTURE.md` to record how MCP audit events are exposed through existing trace outputs.

- Added shared MCP security policy layer (T-2026-06-05-110):
  - Added `src/text_to_sql_agent/services/mcp_security_policy.py` with shared policy validation and enforcement for read-only entrypoints, denied operations, and optional schema allowlists.
  - Updated `src/text_to_sql_agent/agents/query_execution_agent.py` to enforce policy before any MCP-backed query execution.
  - Updated `src/text_to_sql_agent/agents/security_guard_agent.py` to reuse shared policy validation and keep suspicious-pattern detection behavior.
  - Exported policy helpers from `src/text_to_sql_agent/services/__init__.py`.
  - Added focused tests in `tests/text_to_sql_agent/services/test_mcp_security_policy.py` and extended focused agent tests in `tests/text_to_sql_agent/agents/test_query_execution_agent.py`.
  - Updated `docs/ARCHITECTURE.md` to record the shared pre-execution MCP policy boundary.

- Wired query execution agent to dialect-aware MCP adapter factory (T-2026-06-05-108):
  - Updated `src/text_to_sql_agent/repositories/query_execution_factory.py` to construct dialect-specific MCP adapters for SQLite, PostgreSQL, and Athena.
  - Added MCP-backed query execution wrapper behavior that maps canonical MCP execute payloads into the existing execution result shape.
  - Updated `src/text_to_sql_agent/agents/query_execution_agent.py` to pass runtime connection config into the dialect-aware factory.
  - Updated focused tests in `tests/text_to_sql_agent/repositories/test_query_execution_repository.py` and validated `tests/text_to_sql_agent/agents/test_query_execution_agent.py`.
  - Updated `docs/ARCHITECTURE.md` to document that query execution now uses the MCP-backed dialect-aware factory path.

- Added Athena concrete MCP query execution adapter (T-2026-06-05-107):
  - Added `src/text_to_sql_agent/repositories/athena_mcp_client_repository.py` implementing canonical `mcp.db.execute`, `mcp.db.schema`, and `mcp.db.health` operations for Athena via an invoker boundary.
  - Added normalized success/error envelope mapping for execution, schema, and health flows, including timeout/transport error mapping.
  - Exported `AthenaMCPClientRepository` from `src/text_to_sql_agent/repositories/__init__.py`.
  - Added focused repository tests in `tests/text_to_sql_agent/repositories/test_athena_mcp_client_repository.py`.
  - Updated `docs/ARCHITECTURE.md` to note all currently implemented concrete MCP adapters in the repository layer.

- Added PostgreSQL concrete MCP query execution adapter (T-2026-06-05-106):
  - Added `src/text_to_sql_agent/repositories/postgresql_mcp_client_repository.py` implementing canonical `mcp.db.execute`, `mcp.db.schema`, and `mcp.db.health` operations for PostgreSQL.
  - Added normalized success/error envelope mapping for execution, schema, and health flows.
  - Exported `PostgreSQLMCPClientRepository` from `src/text_to_sql_agent/repositories/__init__.py`.
  - Added focused repository tests in `tests/text_to_sql_agent/repositories/test_postgresql_mcp_client_repository.py`.
  - Updated `docs/ARCHITECTURE.md` to note concrete MCP adapters in the repository layer.

- Added SQLite concrete MCP query execution adapter (T-2026-06-05-105):
  - Added `src/text_to_sql_agent/repositories/sqlite_mcp_client_repository.py` implementing canonical `mcp.db.execute`, `mcp.db.schema`, and `mcp.db.health` operations for SQLite.
  - Added normalized success/error envelope mapping for execution, schema, and health flows.
  - Exported `SQLiteMCPClientRepository` from `src/text_to_sql_agent/repositories/__init__.py`.
  - Added focused repository tests in `tests/text_to_sql_agent/repositories/test_sqlite_mcp_client_repository.py`.
  - Updated `docs/ARCHITECTURE.md` to note the first concrete MCP adapter in the repository layer.

- Added abstract MCP client repository contract (T-2026-06-05-104):
  - Added `src/text_to_sql_agent/repositories/mcp_client_repository.py` with the canonical repository-layer interface for `mcp.db.execute`, `mcp.db.schema`, and `mcp.db.health` operations.
  - Exported the contract from `src/text_to_sql_agent/repositories/__init__.py`.
  - Added focused abstract-interface tests in `tests/text_to_sql_agent/repositories/test_mcp_client_repository.py`.
  - Updated `docs/ARCHITECTURE.md` to record the repository-layer source of truth for MCP adapter behavior.

- Added MCP runtime settings by dialect (T-2026-06-05-109):
  - Added typed MCP adapter runtime settings and `load_mcp_runtime_settings()` in `src/text_to_sql_agent/config/settings.py`.
  - Added config exports in `src/text_to_sql_agent/config/__init__.py`.
  - Added focused config tests in `tests/text_to_sql_agent/config/test_mcp_runtime_settings.py`.
  - Added explicit MCP config keys to `.env`, `.env.dev`, `.env.prod`, and `.env.test` for SQLite, PostgreSQL, and Athena.
  - Updated `docs/ARCHITECTURE.md` with the canonical MCP runtime configuration keys.

- Added MCP server setup guide for SQLite, PostgreSQL, and Athena (T-2026-06-05-103):
  - Expanded `README.md` with required environment inputs, authentication guidance, startup command templates, and preflight validation commands.
  - Documented contract-level validation flow using `mcp.db.health`, `mcp.db.schema`, and `mcp.db.execute`.
  - Updated `docs/ARCHITECTURE.md` to point to the setup reference and clarify that MCP servers remain external infrastructure.

- Added canonical MCP tool contract v1 for DB adapter integration (T-2026-06-05-102):
  - Added `src/text_to_sql_agent/models/mcp_contract.py` with typed request and response models for `mcp.db.execute`, `mcp.db.schema`, and `mcp.db.health`.
  - Added canonical error taxonomy codes and error envelope fields used by MCP adapter responses.
  - Exported MCP contract models in `src/text_to_sql_agent/models/__init__.py`.
  - Added focused model tests in `tests/text_to_sql_agent/models/test_mcp_contract.py`.
  - Updated `docs/ARCHITECTURE.md` with canonical tool names, request/response baseline schemas, and error taxonomy.

- Added MCP integration architecture decision and boundary definition (T-2026-06-05-101):
  - Added D-2026-06-05-023 in `docs/DECISIONS.md` to adopt MCP-backed database access for SQLite, PostgreSQL, and Athena via repository adapters.
  - Defined scope constraints for read-only query and schema-access tools, with destructive operations out of scope.
  - Defined security and reliability baseline requirements (deny-by-default read-only policy, allowlists, timeouts/retries, normalized error contracts, structured audit events).
  - Updated `docs/ARCHITECTURE.md` with MCP boundary constraints, lifecycle integration, and phased rollout sequence.

- Added explicit Pydantic field descriptions for `SchemaSnapshotRef` core attributes (T-2026-06-05-100):
  - Updated `src/text_to_sql_agent/models/lifecycle.py` so `snapshot_id`, `database_id`, `dialect`, `created_at`, and `table_count` use `Field(description=...)` metadata.
  - Preserved existing runtime behavior while improving model metadata readability.


## 2026-06-01

### Planned

_None_

### Added

- Added explicit Pydantic field descriptions for `RawIntrospectionResult` attributes (T-2026-06-01-099):
  - Updated `src/text_to_sql_agent/models/introspection.py` so `RawIntrospectionResult` uses `Field(description=...)` for all attributes.
  - Preserved `default_factory` defaults and existing runtime behavior while improving model metadata readability.

- Added explicit Pydantic field descriptions for `RawTableMeta` attributes (T-2026-06-01-098):
  - Updated `src/text_to_sql_agent/models/introspection.py` so `RawTableMeta` uses `Field(description=...)` for all attributes.
  - Preserved optional defaults and existing runtime behavior while improving model metadata readability.

- Added explicit Pydantic field descriptions for `RawIndexMeta` attributes (T-2026-06-01-097):
  - Updated `src/text_to_sql_agent/models/introspection.py` so `RawIndexMeta` uses `Field(description=...)` for all attributes.
  - Preserved optional defaults and existing runtime behavior while improving model metadata readability.

- Added explicit Pydantic field descriptions for `RawForeignKeyMeta` attributes (T-2026-06-01-096):
  - Updated `src/text_to_sql_agent/models/introspection.py` so `RawForeignKeyMeta` uses `Field(description=...)` for all attributes.
  - Preserved optional defaults and existing runtime behavior while improving model metadata readability.

- Added explicit Pydantic field descriptions for `RawColumnMeta` attributes (T-2026-06-01-095):
  - Updated `src/text_to_sql_agent/models/introspection.py` so `RawColumnMeta` uses `Field(description=...)` for all attributes.
  - Preserved optional defaults and existing runtime behavior while improving model metadata readability.

- Strengthened task-trace CI enforcement to require WORKLOG updates (T-2026-06-01-094):
  - Updated `.github/workflows/task-trace-check.yml` to require both `docs/TASKS.md` and `docs/WORKLOG.md` whenever pull requests include changes in `src/` or `tests/`.
  - Prevents implementation changes from being merged without a corresponding worklog entry.

- Added mandatory task-trace completion gate and CI enforcement (T-2026-06-01-093):
  - Updated `.github/copilot-instructions.md` with a required completion gate for `docs/TASKS.md`, `docs/WORKLOG.md`, and conditionally `docs/CHANGELOG.md`.
  - Added `.github/workflows/task-trace-check.yml` to fail pull requests when `src/` or `tests/` change without a corresponding update to `docs/TASKS.md`.
  - Reduces risk of completed implementation tasks being left undocumented.

- Added explicit Pydantic field descriptions for canonical schema models (T-2026-06-01-092):
  - Updated `src/text_to_sql_agent/models/schema.py` to add `Field(description=...)` metadata across `ForeignKeySchema`, `ColumnSchema`, `TableSchema`, and `DatabaseSchema`.
  - Improves schema readability and model introspection metadata without changing runtime behavior.


## 2026-05-29

### Planned

_None_

### Added

- Functional-style migration RFC (T-2026-05-29-086):
  - Added `docs/RFC_FUNCTIONAL_STYLE.md` with functional-style scope, non-goals, migration rules, pilot modules, and rollout criteria.
  - Linked the RFC from `docs/ARCHITECTURE.md` and documented the functional-core / imperative-shell split in the architecture reference.

- Pure query insight derivation helpers (T-2026-05-29-089):
  - Added `src/text_to_sql_agent/services/query_insights_derivation.py` with deterministic helpers for no-row handling, row/column counting, and chart metadata summarization.
  - Refactored `src/text_to_sql_agent/services/query_insights.py` into a thin wrapper that preserves the `QueryInsightResult` API.
  - Added focused tests for the pure derivation helpers in `tests/text_to_sql_agent/services/test_query_insights_derivation.py`.

- Pure chart derivation helpers for query analytics (T-2026-05-29-088):
  - Added `src/text_to_sql_agent/services/query_analytics_derivation.py` with deterministic helpers for numeric/categorical detection and chart derivation strategies.
  - Refactored `src/text_to_sql_agent/services/query_analytics.py` into a thin wrapper that preserves the `QueryAnalyticsResult` API.
  - Added focused tests for the pure derivation helpers in `tests/text_to_sql_agent/services/test_query_analytics_derivation.py`.

- Pure render-model builders for Chainlit UI rendering (T-2026-05-29-087):
  - Added `src/text_to_sql_agent/ui/render_models.py` with pure builders for SQL preview, conversation labels, markdown tables, and Plotly figures.
  - Refactored `src/text_to_sql_agent/ui/renderers.py` into a thin adapter layer that preserves the existing public API.
  - Added deterministic tests for the normalized render models in `tests/text_to_sql_agent/ui/test_render_models.py`.

- Functional-style review checklist and Definition of Done (T-2026-05-29-091):
  - Added `docs/FUNCTIONAL_STYLE_REVIEW_CHECKLIST.md` for PRs that touch functional-core code paths.
  - Defined a concise reviewer checklist for purity, explicit dependencies, deterministic transformations, boundary isolation, and test coverage.
  - Added a compact Definition of Done section to standardize acceptance criteria for this review style.
  - Linked the checklist from `docs/AGENTS.md` and added `.github/PULL_REQUEST_TEMPLATE.md` to surface the review standard in the PR flow.

- Functional-style project instruction boundaries (T-2026-05-29-090):
  - Added a new **Functional Style Requirement** section to `.github/copilot-instructions.md`.
  - Defined functional-first scope for core logic in `services`, pure transformations in `agents`, and data-shaping helpers in `utils`.
  - Defined imperative boundary scope for `ui`, `repositories`, and app entrypoints (`main.py`, `main_chainlit.py`, `main_terminal.py`).
  - Added explicit guideline: target architecture is **functional core, imperative shell**.

- Conversation DB location alignment and cleanup (T-2026-05-29-085):
  - Added `CONVERSATION_DB_PATH=tests/text_to_sql_agent/db/conversation.db` to `.env`, `.env.dev`, `.env.test`, and `.env.prod`.
  - Consolidated conversation storage under `tests/text_to_sql_agent/db/conversation.db`.
  - Moved accidentally created root `conversation.db` into the test DB folder.
  - Removed temporary backup artifact after validating the move.

- Chainlit JWT secret configuration (T-2026-05-29-084):
  - Updated `main_chainlit.py` launcher to pass `CHAINLIT_AUTH_SECRET` via subprocess environment variable (not CLI flag).
  - Modified `_build_runtime_env()` to include JWT secret in subprocess environment variables for Chainlit to read.
  - Added warning log when JWT secret is missing (authentication unavailable).
  - Added `CHAINLIT_AUTH_SECRET` to all `.env` files (`.env`, `.env.dev`, `.env.prod`, `.env.test`).
  - Development: uses concrete JWT secret value for local development.
  - Testing: uses separate concrete value for test environment.
  - Production: uses `[LOAD_FROM_SECRETS]` placeholder for runtime secret resolution from AWS Secrets Manager or HashiCorp Vault.
  - JWT secret automatically resolved through `load_runtime_environment()` launcher setup.
  - Verified launcher starts successfully: Chainlit server starts at http://localhost:8000 without CLI errors.
  - Enables persistent user authentication and session management in Chainlit web UI.


- Updated auth and user-scoped history architecture documentation (T-2026-05-28-083):
  - Expanded `docs/ARCHITECTURE.md` with implemented username/password auth flow and callback/service/repository boundaries.
  - Added explicit conversation persistence model over shared `users`/`conversations`/`messages` schema.
  - Added ownership-enforcement and user-isolation description for conversation history access.
  - Added Chainlit history UX lifecycle for `on_chat_start`, `open_conversation`, and `new_conversation` behavior.

- Added integration tests for auth and conversation resume flow (T-2026-05-28-082):
  - New `tests/text_to_sql_agent/ui/test_chainlit_auth_and_history.py` covers password auth callback success, chat-start identity wiring, opening an existing conversation, follow-up continuation in the opened conversation, and cross-user open denial.

- Added expanded service tests for history filtering (T-2026-05-28-081):
  - Updated `tests/text_to_sql_agent/services/test_conversation_history_service.py` with newest-first ordering checks and empty-conversation loading behavior, alongside strict ownership and missing-conversation access checks.

- Added focused SQLite session repository persistence tests (T-2026-05-28-080):
  - Added `tests/text_to_sql_agent/repositories/test_sqlite_session_repository.py` coverage for durable user/conversation/message persistence, metadata/role roundtrip, ordering, duplicate handling, and user/conversation isolation.

- Added focused SQLite auth repository persistence tests (T-2026-05-28-079):
  - Added `tests/text_to_sql_agent/repositories/test_sqlite_auth_repository.py` coverage for account creation, duplicate constraints, username/user-id lookups, password-hash updates, active-flag toggles, and account existence checks.

- Added Chainlit `open_conversation` callback with persisted history loading (T-2026-05-28-078):
  - Updated `src/text_to_sql_agent/ui/chainlit_app.py` to validate selected conversation ownership, switch active conversation state, and render persisted messages from storage.
  - Added focused callback coverage in `tests/text_to_sql_agent/ui/test_chainlit_app.py`.

- Added Chainlit `new_conversation` callback and action wiring (T-2026-05-28-077):
  - Updated `src/text_to_sql_agent/ui/chainlit_app.py` to expose `Start new conversation` action in history messages and create a new active conversation without removing history access.
  - Added focused callback coverage in `tests/text_to_sql_agent/ui/test_chainlit_app.py`.

- Added user conversation-history list rendering in Chainlit chat UI (T-2026-05-28-076):
  - Updated `src/text_to_sql_agent/ui/chainlit_app.py` to list authenticated-user conversations on chat start.
  - Added `open_conversation` action buttons carrying `conversation_id` payloads for user-selected history items.
  - Wired `_get_runtime()` to use `SQLiteSessionRepository` from env-backed conversation settings (`CONVERSATION_DB_PATH`), enabling durable history visibility.
  - Added compact conversation-action label rendering in `src/text_to_sql_agent/ui/renderers.py` and exported it from `src/text_to_sql_agent/ui/__init__.py`.
  - Added focused UI tests in `tests/text_to_sql_agent/ui/test_chainlit_app.py` and `tests/text_to_sql_agent/ui/test_renderers.py`.

## 2026-05-28

### Added

- Added persistent LangGraph thread-id tracking per conversation (T-2026-05-28-075):
  - Extended `Conversation` model with optional `graph_thread_id` in `src/text_to_sql_agent/models/session.py`.
  - Updated `src/text_to_sql_agent/repositories/sqlite_session_repository.py` to persist and hydrate `graph_thread_id`.
  - Updated `src/text_to_sql_agent/ui/handlers.py` to reuse persisted thread IDs for existing conversations and to persist explicit thread overrides.
  - Added focused tests in `tests/text_to_sql_agent/models/test_session.py`, `tests/text_to_sql_agent/repositories/test_sqlite_session_repository.py`, and `tests/text_to_sql_agent/ui/test_handlers.py`.

- Added conversation history service with strict ownership validation (T-2026-05-28-074):
  - New `src/text_to_sql_agent/services/conversation_history_service.py` with `ConversationHistoryService`, `ConversationAccessError`, and `ConversationHistoryRecord`.
  - `load_user_conversation()` now verifies that the requested conversation belongs to the requesting user before returning messages.
  - Exported via `src/text_to_sql_agent/services/__init__.py`.
  - Added focused tests in `tests/text_to_sql_agent/services/test_conversation_history_service.py`.

- Wired authenticated user identity into Chainlit session state (T-2026-05-28-073):
  - Updated `src/text_to_sql_agent/ui/chainlit_app.py` to resolve `user_id`, `username`, and `display_name` from `cl.user_session.get("user")` instead of generating random user IDs.
  - Added `_resolve_authenticated_identity()` helper with safe fallback values when session user metadata is unavailable.
  - Updated chat-start session initialization to persist resolved identity fields for downstream UI/runtime logic.
  - Added focused tests in `tests/text_to_sql_agent/ui/test_chainlit_app.py`.

- Added Chainlit password auth callback integration (T-2026-05-28-072):
  - New `src/text_to_sql_agent/ui/auth_callbacks.py` with `build_auth_service_from_env()`, `authenticate_with_password()`, `make_chainlit_user()`.
  - Registered `@cl.password_auth_callback` in `src/text_to_sql_agent/ui/chainlit_app.py`; returns `cl.User` on success, `None` to reject.
  - Core auth logic (`authenticate_with_password`) is Chainlit-free for testability.
  - Exported from `src/text_to_sql_agent/ui/__init__.py`. 8 tests pass.

- Added auth service with register-or-login policy and Argon2id password hashing (T-2026-05-28-071):
  - New `src/text_to_sql_agent/services/auth_service.py` with `AuthService`, `AuthError`, `AuthResult`, `hash_password()`, `verify_password()`.
  - `authenticate_or_register()` supports auto-register-on-first-login (env-driven), wrong-password rejection, and inactive-account blocking.
  - `register()` for explicit registration with duplicate-username and min-length enforcement.
  - Added `argon2-cffi` to project dependencies (`pyproject.toml`, `uv.lock`).
  - Exported from `src/text_to_sql_agent/services/__init__.py`. 19 tests pass.

- Added SQLite auth repository for user account persistence (T-2026-05-28-070):
  - New `SQLiteAuthRepository` in `src/text_to_sql_agent/repositories/sqlite_auth_repository.py`.
  - Supports account creation (raises `ValueError` on duplicate username/user_id), lookup by username and user_id, username existence check, password hash update, and account activation toggle.
  - Exported from `src/text_to_sql_agent/repositories/__init__.py`. 17 tests pass.

- Added persistent SQLite session repository (T-2026-05-28-069):
  - New `SQLiteSessionRepository` in `src/text_to_sql_agent/repositories/sqlite_session_repository.py` replaces volatile in-memory session storage.
  - Supports user upsert (INSERT OR IGNORE), conversation save/update/list with user-scoped isolation, and message append/list with ordering by `created_at`.
  - JSON roundtrip for `metadata` fields on both conversations and messages.
  - Updated `conversation_db.py` schema to add `metadata_json` column to `conversations` table.
  - Exported from `src/text_to_sql_agent/repositories/__init__.py`. 18 tests pass.

- Added conversation database bootstrap module (T-2026-05-28-068):
  - New `src/text_to_sql_agent/repositories/conversation_db.py` with `bootstrap_schema()`, `get_connection()`, `managed_connection()`.
  - Schema: `users` (unique username, password_hash), `conversations` (FK to users, graph_thread_id), `messages` (FK to conversations) with appropriate indexes.
  - Idempotent — safe to call on every startup. Auto-creates parent directories.
  - Exported from `src/text_to_sql_agent/repositories/__init__.py`. 12 tests pass.

- Added auth-facing Pydantic models for username/password flow (T-2026-05-28-067):
  - Introduced `UserAccount`, `UserRegistration`, `UserLogin`, `AuthPrincipal` in `src/text_to_sql_agent/models/auth.py`.
  - `UserRegistration` validates and strips username, enforces min-length for both fields, and resolves display name from username when blank.
  - `AuthPrincipal.from_account()` builds a safe identity object (no password hash) from a persisted `UserAccount`.
  - Exported from `src/text_to_sql_agent/models/__init__.py`.
  - Added 17 focused tests in `tests/text_to_sql_agent/models/test_auth.py`.

- Added conversation/auth runtime settings loader for upcoming persistent chat history work (T-2026-05-28-066):
  - Introduced `ConversationAuthSettings` and `load_conversation_auth_settings()` in `src/text_to_sql_agent/config/settings.py`.
  - Added environment-driven settings for `CONVERSATION_DB_PATH`, `AUTH_AUTO_REGISTER_ON_FIRST_LOGIN`, and `AUTH_MIN_PASSWORD_LENGTH`.
  - Exported the new settings API from `src/text_to_sql_agent/config/__init__.py`.
  - Added focused config coverage in `tests/text_to_sql_agent/config/test_conversation_auth_settings.py`.

## 2026-05-26

### Added

- Fixed Chainlit runtime secret loading for LLM key (T-2026-05-26-065):
  - Updated `main_chainlit.py` to load runtime environment and resolve secret placeholders before launching Chainlit.
  - Ensures `LLM_API_KEY` from `.secrets.local.json` is available to SQL generation in web flow.
  - Added `src/` import-path safeguard for launcher-side config import.

- Added visible SQL generation mode marker in Chainlit preview (T-2026-05-26-064):
  - SQL approval message now shows generation mode as `LLM`, `Few-shot fallback`, or `Deterministic`.
  - Added `sql_generation_mode` propagation from SQL generator node through query state to UI rendering.
  - Added focused tests for node output and Chainlit message content.

- Improved fallback SQL relevance and web transparency when LLM is unavailable (T-2026-05-26-063):
  - Updated `src/text_to_sql_agent/agents/sql_generator_agent.py` with stronger few-shot matching: exact-phrase preference, country-code extraction, and numeric entity scoring.
  - Added LLM status tracking and user notice fields for SQL generation output.
  - Updated Chainlit SQL approval rendering in `src/text_to_sql_agent/ui/chainlit_app.py` to show a notice when deterministic fallback is used because LLM is unavailable.
  - Added focused tests in `tests/text_to_sql_agent/agents/test_sql_generator_agent.py` and `tests/text_to_sql_agent/ui/test_chainlit_app.py`.

- Improved SQL generation fallback to use few-shot examples when LLM is unavailable (T-2026-05-26-062):
  - Updated `src/text_to_sql_agent/agents/sql_generator_agent.py` so deterministic mode first tries to match a relevant table-aware few-shot example and reuse its SQL.
  - Prevents generic `SELECT * ... LIMIT` responses for questions that already have explicit few-shot patterns.
  - Added regression coverage in `tests/text_to_sql_agent/agents/test_sql_generator_agent.py`.

- Improved Chainlit shell launcher resiliency (T-2026-05-26-061):
  - Updated `run_main_chainlit.sh` to validate launcher paths and auto-select an available localhost port when `CHAINLIT_PORT` is unset.
  - Prevents startup failure when port `8000` is already occupied.

- Connected SQL prompt builder to real LLM SQL generation (T-2026-05-26-060):
  - Updated `src/text_to_sql_agent/agents/sql_generator_agent.py` to execute an LLM generation step from the rendered SQL prompt.
  - Added environment-driven controls and model resolution for runtime (`SQL_GENERATOR_LLM_ENABLED`, `OPENAI_MODEL`, API key aliases).
  - Added read-only safety checks and fenced-output SQL extraction for LLM responses.
  - Added deterministic fallback path when LLM generation is unavailable, fails, or returns unsafe SQL.
  - Added focused agent tests in `tests/text_to_sql_agent/agents/test_sql_generator_agent.py`.

- Added table-aware few-shot filtering and selected-table propagation (T-2026-05-26-059):
  - Extended `FewShotExample` with table metadata and added `get_few_shot_examples_for_tables(...)` in `src/text_to_sql_agent/prompts/few_shot_examples.py`.
  - Added `src/text_to_sql_agent/prompts/sql_generation_prompt.py` to build SQL generation prompts with schema context and filtered few-shot examples.
  - Propagated `selected_tables` through query state/UI and schema-context loading:
    - `src/text_to_sql_agent/graphs/query_state.py`
    - `src/text_to_sql_agent/ui/handlers.py`
    - `src/text_to_sql_agent/agents/schema_context_agent.py`
  - Wired SQL generator observability to expose rendered prompt and filtered few-shot count in `src/text_to_sql_agent/agents/sql_generator_agent.py`.
  - Added focused tests for prompts, agents, graph, and UI handler propagation.

## 2026-05-19

### Added

- Adjusted Chainlit result message order for export visibility (T-2026-05-19-058):
  - Updated `src/text_to_sql_agent/ui/chainlit_app.py` so export actions are rendered before the optional chart.
  - Added a focused ordering test in `tests/text_to_sql_agent/ui/test_chainlit_app.py`.

- Added Plotly as a project dependency for Chainlit charts (T-2026-05-19-057):
  - Updated `pyproject.toml` and `uv.lock` with `plotly>=6.7.0`.
  - Synced both `venvtext2sql` and the uv-managed `.venv` so chart rendering works in either launcher path.
  - Restored the optional chart UI on successful query execution while preserving export actions.

- Hardened Chainlit result rendering when Plotly is unavailable (T-2026-05-19-056):
  - Updated `src/text_to_sql_agent/ui/chainlit_app.py` to skip `cl.Plotly` element creation when the optional `plotly` package is not installed.
  - Prevented `ModuleNotFoundError` from aborting the response before export actions are rendered.
  - Added focused fallback coverage in `tests/text_to_sql_agent/ui/test_chainlit_app.py`.

- Fixed Chainlit export actions visibility (T-2026-05-19-055):
  - Updated `src/text_to_sql_agent/ui/chainlit_app.py` `_render_query_result()` to attach CSV/JSON export action buttons directly to the insight message instead of a separate message.
  - Export actions now appear alongside query insights, improving button discoverability and reducing UI clutter.

- Fixed Chainlit app imports for uv runtime (T-2026-05-19-054):
  - Updated `main_chainlit.py` subprocess execution to set `cwd` to project root and inject `PYTHONPATH` with `src` + project root.
  - Resolved `ModuleNotFoundError: text_to_sql_agent` when launching via `uv run chainlit`.
  - Added `chainlit.md` to `.gitignore` as local Chainlit runtime artifact.

- Improved Chainlit launcher compatibility (T-2026-05-19-053):
  - Updated `main_chainlit.py` to resolve Chainlit using three-step fallback: `python -m chainlit`, `chainlit` binary, then `uv run chainlit`.
  - Added clearer startup and failure messaging, including the exact command used when process startup fails.
  - Launcher now works in setups where dependencies are installed in uv-managed environment but not in `venvtext2sql`.

- Observability and audit trail for agent runs (T-2026-05-18-052):
  - New `src/text_to_sql_agent/models/trace.py` with `AgentEvent` and `AuditTrail` Pydantic models for structured per-node tracing with user/conversation identity linkage.
  - New `src/text_to_sql_agent/services/audit_trail.py` with `make_agent_event()` factory (returns a plain dict for LangGraph serialisation) and `build_audit_trail()` to reconstruct a typed trail from a completed `QueryState`.
  - Extended `QueryState` with `agent_events: Annotated[list[dict], _append]` field so every pipeline node can append its structured event.
  - All pipeline nodes (`schema_context`, `sql_generator`, `syntax_validator`, `security_guard`, `human_approval`, `query_executor`, `node_done`, `node_failed`) now emit a structured `AgentEvent` dict alongside their existing `log_messages`.
  - New tests: `tests/text_to_sql_agent/models/test_trace.py` (9 cases) and `tests/text_to_sql_agent/services/test_audit_trail.py` (9 cases).

## 2026-05-18

### Changed

- Added Chainlit UI flow for DB assistant (T-2026-05-18-051):
  - New `src/text_to_sql_agent/ui/chainlit_app.py` implementing chat flow with SQL preview, approval actions, result rendering, and export actions.
  - New `src/text_to_sql_agent/ui/handlers.py` with LangGraph-driven turn orchestration and explicit pause/resume handling for human approval.
  - New `src/text_to_sql_agent/ui/renderers.py` for SQL/table/chart rendering helpers used by the Chainlit layer.
  - Added UI-focused tests in `tests/text_to_sql_agent/ui/test_handlers.py` and `tests/text_to_sql_agent/ui/test_renderers.py`.
  - Added `chainlit` dependency to `pyproject.toml` and updated lockfile.

- Added insights agent for post-query conclusions (T-2026-05-18-050):
  - New `src/text_to_sql_agent/services/query_insights.py` to generate concise narrative insight text from `execution_result` and `chart_spec`.
  - New `src/text_to_sql_agent/agents/insights_agent.py` with `build_insights_node()` for LangGraph integration.
  - `src/text_to_sql_agent/graphs/query_graph.py` now includes a dedicated `insights` step between analytics and export.
  - Added focused tests in `tests/text_to_sql_agent/services/test_query_insights.py` and `tests/text_to_sql_agent/agents/test_insights_agent.py`.

- Added analytics agent and one-shot chart service (T-2026-05-18-049):
  - New `src/text_to_sql_agent/services/query_analytics.py` with deterministic one-shot chart generation from `execution_result`.
  - New `src/text_to_sql_agent/agents/analytics_agent.py` with `build_analytics_node()` integration for LangGraph.
  - Analytics now supports category+numeric aggregation, categorical counts, numeric line fallback, and empty-result handling.
  - `src/text_to_sql_agent/graphs/query_graph.py` now uses the analytics agent node instead of inline analytics stub.
  - Added focused tests in `tests/text_to_sql_agent/services/test_query_analytics.py` and `tests/text_to_sql_agent/agents/test_analytics_agent.py`.

- Added data export agent and export service (T-2026-05-18-048):
  - New `src/text_to_sql_agent/services/query_result_export.py` to export existing query results to CSV/JSON and optional XLSX.
  - New `src/text_to_sql_agent/agents/export_agent.py` with `build_export_node()` and `export_execution_result()`.
  - Export flow now uses only `execution_result` payload (no SQL re-execution).
  - `src/text_to_sql_agent/graphs/query_graph.py` now uses export agent node instead of inline export stub.
  - Added focused tests in `tests/text_to_sql_agent/services/test_query_result_export.py` and `tests/text_to_sql_agent/agents/test_export_agent.py`.

- Added query execution agent and repository-backed execution path (T-2026-05-18-047):
  - New `src/text_to_sql_agent/agents/query_execution_agent.py` with read-only enforcement and normalized execution payload.
  - New query execution repository contract/factory and SQLite implementation:
    - `src/text_to_sql_agent/repositories/query_execution_repository.py`
    - `src/text_to_sql_agent/repositories/sqlite_query_execution_repository.py`
    - `src/text_to_sql_agent/repositories/query_execution_factory.py`
  - `src/text_to_sql_agent/graphs/query_graph.py` now uses `build_query_execution_node(connection_config)` instead of inline execution stub.
  - Added focused tests for the new agent and repository modules.

- Added human approval gate agent (T-2026-05-18-046):
  - New `src/text_to_sql_agent/agents/human_approval_agent.py` with normalized decision handling for `approve`, `reject/cancel`, and `edit` actions.
  - Added `build_human_approval_node()` LangGraph adapter with explicit state transitions before execution.
  - Human approval logic in `src/text_to_sql_agent/graphs/query_graph.py` is now delegated to the dedicated agent module.
  - Added focused tests in `tests/text_to_sql_agent/agents/test_human_approval_agent.py`.

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

