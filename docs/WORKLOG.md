# Work Log

This file stores a chronological log of work performed on the project.

Rules:
- Keep entries concise and factual.
- Reference task IDs from `docs/TASKS.md`.
- Write every entry in English.

## 2026-05-11

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
