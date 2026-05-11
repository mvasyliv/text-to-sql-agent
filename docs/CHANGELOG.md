# Changelog

All notable changes to this project will be documented in this file.

The format is intentionally simple and uses dated sections until versioned releases are introduced.

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

### Changed

- Documentation workflow now requires recording tasks in `docs/TASKS.md`, implementation history in `docs/WORKLOG.md`, durable decisions in `docs/DECISIONS.md`, and notable project changes in `docs/CHANGELOG.md`.
- The canonical changelog location was moved from the repository root to `docs/CHANGELOG.md`.
- Updated repository instructions to document `venvtext2sql` as the canonical virtual environment and `uv` as the package manager.
- Updated VS Code Python configuration to always show the selected interpreter in the status bar, making the canonical `venvtext2sql` environment visible during development.