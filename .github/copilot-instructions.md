# Text-to-SQL Agent Project Instructions

## Scope

This repository is a Python 3.13 project for building a text-to-SQL agent. Keep changes focused, minimal, and consistent with the existing package layout under `src/text_to_sql_agent/`.

## Environment Setup

- **Virtual environment**: `venvtext2sql/` is the canonical virtual environment for this project.
- **Package manager**: Use `uv` to manage dependencies. The `uv.lock` file is the source of truth for pinned versions.
- **Python version**: Pinned to 3.13 in `.python-version` and `pyproject.toml`.
- **VS Code integration**: `.vscode/settings.json` configures VS Code to automatically activate the `venvtext2sql` environment.

To work with the project:
```bash
# Activate the environment (if not auto-activated in VS Code)
source venvtext2sql/bin/activate

# Install or update dependencies with uv
uv sync
```

## Language Rule

All documentation, code comments, commit-style summaries, user-facing technical explanations, and generated project notes must be written in English, regardless of the language used in the prompt or by the user.

This rule applies to:
- Markdown documentation
- Docstrings
- Inline code comments
- README content
- Architecture notes
- Test names and test descriptions when newly added
- Explanations written into project files

## Project Structure

- `src/text_to_sql_agent/agents/`: agent orchestration and agent-specific logic
- `src/text_to_sql_agent/graphs/`: workflow and graph definitions
- `src/text_to_sql_agent/services/`: service-layer logic and integrations
- `src/text_to_sql_agent/repositories/`: database and persistence access
- `src/text_to_sql_agent/models/`: data models and schemas
- `src/text_to_sql_agent/prompts/`: prompt templates and prompt-building utilities
- `src/text_to_sql_agent/config/`: runtime and environment configuration
- `src/text_to_sql_agent/utils/`: small shared helpers
- `tests/`: automated tests
- `main.py`: simple entry point; keep it thin

## Implementation Expectations

- Prefer root-cause fixes over superficial patches.
- Keep public interfaces stable unless the task explicitly requires a change.
- Reuse existing modules and abstractions before introducing new ones.
- Avoid speculative abstractions and premature generalization.
- Keep functions cohesive and names explicit.
- Use type hints for new or modified Python code.
- Prefer Pydantic models or existing schema patterns where structured validation is already part of the design.

## Editing Rules

- Preserve the current repository style and naming conventions.
- Do not add dependencies unless they are necessary for the task.
- Do not rewrite unrelated files.
- When creating new modules, place them in the most specific existing package.
- Keep comments brief and only add them when the code is not self-explanatory.
- Every `__init__.py` must declare `__version__ = "0.0.1"` (or the current package version) immediately after the module docstring.

## Validation

After code changes, prefer the narrowest relevant validation first:
- targeted `pytest` tests for the affected area
- `ruff` for linting if configured for the touched files
- `mypy` for typing-sensitive changes

If no focused test exists, add or update one when the change affects behavior that can be verified automatically.

## Documentation

- Update documentation when behavior, setup, configuration, or architecture changes.
- Keep examples realistic and synchronized with the current code.
- If a file is currently empty or missing documentation, add only the documentation necessary for the requested task.
- Maintain `docs/ARCHITECTURE.md` as the living reference for the system structure and request flow.
- Record notable project changes in `docs/CHANGELOG.md`.
- Record each project task in `docs/TASKS.md`.
- Record implementation history in `docs/WORKLOG.md` when work is performed.
- Record durable process or architecture decisions in `docs/DECISIONS.md` when relevant.

## Configuration And Secrets

- Do not hardcode secrets, API keys, DSNs, or credentials.
- Prefer environment-based configuration.
- Keep `.env` usage out of committed source files except for documented placeholders or examples.

## Testing Guidance

- Prefer deterministic tests.
- Mock external services when practical.
- Keep fixtures local to the affected test scope unless they are broadly reusable.
- Cover parsing, validation, SQL-generation constraints, and repository/service boundaries when relevant.
- Mirror source package layout in tests: for `src/text_to_sql_agent/<package>/...`, place tests under `tests/text_to_sql_agent/<package>/...`.
- Keep test filenames explicit and aligned with target modules, e.g. `test_prompt_manifest.py` for `prompt_manifest.py`.

## Dependency Management

- Use `uv` instead of `pip` for all dependency operations.
- Run `uv sync` to install dependencies from `pyproject.toml` and `uv.lock`.
- Run `uv add <package>` to add new dependencies (this updates `pyproject.toml` and `uv.lock`).
- Commit both `pyproject.toml` and `uv.lock` so reproducible builds are possible.

## Output Style For Future Edits

When generating project artifacts, keep them concise, technical, and in English.
