# Work Log

This file stores a chronological log of work performed on the project.

Rules:
- Keep entries concise and factual.
- Reference task IDs from `docs/TASKS.md`.
- Write every entry in English.

## 2026-05-15

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
