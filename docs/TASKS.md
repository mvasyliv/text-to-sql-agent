# Project Tasks

This file is the main registry for project work.

Rules:
- Every task must be recorded here.
- Related execution details must be recorded in the supporting files in this directory.
- All entries in this file and supporting files must be written in English.
- Update task status when work starts, changes scope, or completes.

## Statuses

- `planned`: defined but not started
- `in_progress`: currently being worked on
- `done`: completed
- `blocked`: waiting for a dependency or decision

## OPEN

| ID | Date | Title | Status | Summary | Related Files |
| --- | --- | --- | --- | --- | --- |
| _No open tasks_ | - | - | - | Add `planned`, `in_progress`, or `blocked` tasks here (newest to oldest). | - |

## COMPLETED

| ID | Date | Title | Status | Summary | Related Files |
| --- | --- | --- | --- | --- | --- |
| T-2026-05-11-009 | 2026-05-11 | Set up specialized GitHub Copilot agents | done | Created 5 specialized agents (Architect, Task Manager, Developer, Tester, Documentarian) with distinct responsibilities, constraints, and workflows. Each agent has specific instructions for their role. | `.architect.instructions.md`, `.taskmanager.instructions.md`, `.developer.instructions.md`, `.tester.instructions.md`, `.documentarian.instructions.md`, `docs/AGENTS.md`, `docs/TASKS.md`, `docs/WORKLOG.md` |
| T-2026-05-11-008 | 2026-05-11 | Set up loguru-based structured logging | done | Integrated loguru for production-ready logging with JSON output support, per-module log level configuration, file rotation, and compression. Supports stdout, file, and combined output modes. | `src/text_to_sql_agent/config/logging.py`, `pyproject.toml`, `uv.lock`, `docs/TASKS.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md` |
| T-2026-05-11-007 | 2026-05-11 | Set up project configuration system | done | Implemented environment-based configuration system with 4 .env files (template, dev, prod, test) covering all project settings, database drivers (SQLite, PostgreSQL, Athena, MySQL), LLM configuration, caching, feature flags, secrets management, rate limiting, validation, observability, and audit logging. | `.env`, `.env.dev`, `.env.prod`, `.env.test`, `.gitignore`, `docs/TASKS.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md` |
| T-2026-05-11-005 | 2026-05-11 | Configure environment and package management | done | Set up `venvtext2sql` as the canonical virtual environment and `uv` as the package manager; configured VS Code for automatic activation; updated project instructions. | `.vscode/settings.json`, `.github/copilot-instructions.md`, `docs/TASKS.md`, `docs/WORKLOG.md`, `docs/DECISIONS.md`, `docs/CHANGELOG.md` |
| T-2026-05-11-004 | 2026-05-11 | Create initial architecture document | done | Added `docs/ARCHITECTURE.md` as the living reference for the target text-to-SQL system design and documented the main components and request flow. | `docs/ARCHITECTURE.md`, `docs/TASKS.md`, `docs/WORKLOG.md`, `docs/DECISIONS.md`, `docs/CHANGELOG.md`, `.github/copilot-instructions.md` |
| T-2026-05-11-003 | 2026-05-11 | Move changelog into docs | done | Moved the changelog into `docs/` and updated project instructions and history files to use the new path. | `docs/CHANGELOG.md`, `docs/TASKS.md`, `docs/WORKLOG.md`, `docs/DECISIONS.md`, `.github/copilot-instructions.md` |
| T-2026-05-11-002 | 2026-05-11 | Create project changelog | done | Added `docs/CHANGELOG.md` and updated project documentation rules to record project-level changes in a dedicated changelog. | `docs/CHANGELOG.md`, `docs/WORKLOG.md`, `docs/DECISIONS.md`, `.github/copilot-instructions.md` |
| T-2026-05-11-001 | 2026-05-11 | Create project working instructions | done | Added repository-specific Copilot instructions and enforced English-only documentation, comments, and project explanations. | `docs/WORKLOG.md`, `docs/DECISIONS.md`, `.github/copilot-instructions.md` |

## Usage

When adding a new task:
1. Create a new row in the table.
2. Place `done` tasks in `COMPLETED` (newest to oldest).
3. Place `planned`, `in_progress`, and `blocked` tasks in `OPEN` (newest to oldest).
4. When adding the first open task, remove the `_No open tasks_` placeholder row and replace it with the real task row.
5. Add implementation notes to `docs/WORKLOG.md`.
6. Record durable process or architecture decisions in `docs/DECISIONS.md` when relevant.
7. Update `docs/CHANGELOG.md` when the task changes project behavior, structure, process, or documentation expectations.

Example row for `OPEN`:

| ID | Date | Title | Status | Summary | Related Files |
| --- | --- | --- | --- | --- | --- |
| T-YYYY-MM-DD-### | YYYY-MM-DD | Task title | planned | Short description of pending work. | `docs/TASKS.md`, `docs/WORKLOG.md` |

Example row for `COMPLETED`:

| ID | Date | Title | Status | Summary | Related Files |
| --- | --- | --- | --- | --- | --- |
| T-YYYY-MM-DD-### | YYYY-MM-DD | Task title | done | Short description of delivered result. | `docs/TASKS.md`, `docs/WORKLOG.md`, `docs/CHANGELOG.md` |

Checklist template for a new task:

- [ ] Set ID as `T-YYYY-MM-DD-###`.
- [ ] Set `Date` as `YYYY-MM-DD`.
- [ ] Write a short, specific `Title`.
- [ ] Set `Status` (`planned` | `in_progress` | `blocked` | `done`).
- [ ] Add a one-line `Summary`.
- [ ] Add or update the task row in `docs/TASKS.md`.
- [ ] If status is `planned` / `in_progress` / `blocked`, place row in `OPEN` (newest to oldest).
- [ ] If status is `done`, place row in `COMPLETED` (newest to oldest).
- [ ] For the first open task, remove the `_No open tasks_` placeholder row.
- [ ] Add execution notes to `docs/WORKLOG.md`.
- [ ] Add or update `docs/CHANGELOG.md` if project behavior, structure, process, or documentation expectations changed.
- [ ] Add or update `docs/DECISIONS.md` if a durable process or architecture decision was made.

