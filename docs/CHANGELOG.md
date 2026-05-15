# Changelog

All notable changes to this project will be documented in this file.

The format is intentionally simple and uses dated sections until versioned releases are introduced.

## 2026-05-15

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