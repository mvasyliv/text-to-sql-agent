# Project Decisions

This file records durable project-level decisions that affect how work is documented or executed.

Rules:
- Record only decisions that should remain visible over time.
- Reference related task IDs where applicable.
- Write every entry in English.

## D-2026-05-11-001

- Date: 2026-05-11
- Related task: T-2026-05-11-001
- Decision: All project tasks must be recorded in `docs/TASKS.md`, with supporting execution history kept in `docs/WORKLOG.md` and durable decisions recorded in this file.
- Decision: All documentation, comments, and project-facing technical explanations must be written in English, regardless of the user's language.
- Rationale: This keeps project history centralized, reviewable, and consistent across contributors and future sessions.

## D-2026-05-11-002

- Date: 2026-05-11
- Related task: T-2026-05-11-002
- Decision: The repository must maintain `docs/CHANGELOG.md` to record notable project changes in a reader-friendly format.
- Decision: `docs/WORKLOG.md` remains the execution log, while `docs/CHANGELOG.md` summarizes externally relevant project changes.
- Rationale: This separates internal implementation history from a concise project change history and makes review easier over time.

## D-2026-05-11-003

- Date: 2026-05-11
- Related task: T-2026-05-11-003
- Decision: The canonical changelog location for this repository is `docs/CHANGELOG.md`, not the repository root.
- Rationale: This keeps all project documentation and history artifacts grouped under `docs/`.

## D-2026-05-11-004

- Date: 2026-05-11
- Related task: T-2026-05-11-004
- Decision: `docs/ARCHITECTURE.md` is the living reference for the intended system architecture and should be updated when the structure or request flow changes materially.
- Decision: Until implementation details exist, the architecture document may describe the target design explicitly instead of pretending the code already exists.
- Rationale: This keeps design intent visible early and reduces drift between planned structure and future implementation.

## D-2026-05-11-005

- Date: 2026-05-11
- Related task: T-2026-05-11-005
- Decision: `venvtext2sql/` is the canonical virtual environment for this project.
- Decision: `uv` is the canonical package manager; all dependency operations must use `uv` and never `pip`.
- Decision: `uv.lock` is the source of truth for pinned dependency versions and must be committed alongside `pyproject.toml`.
- Decision: VS Code is configured automatically to use `venvtext2sql` as the default Python interpreter via `.vscode/settings.json`.
- Rationale: This ensures reproducible builds, a single source of truth for dependency versions, and automatic environment activation for a frictionless developer experience.

## D-2026-05-11-006

- Date: 2026-05-11
- Related task: T-2026-05-11-010 (scope planning for prompt manifest and governance)
- Decision: Workspace-specific IDE settings (e.g., Markdown Preview styling, optional extensions) that do not affect code behavior must be stored locally in the user's VS Code profile, not in `.vscode/settings.json`.
- Decision: `${VSCODE_USER_PROMPTS_FOLDER}/../User/settings.json` (typically `~/.config/Code/User/settings.json` on Linux) is the prescribed location for personal workspace customizations.
- Decision: `.vscode/` directory is in `.gitignore` to prevent IDE configuration drift across team members.
- Rationale: This separates project-essential configuration (Python interpreter, linting) from personal IDE preferences (preview styling, extensions), avoiding unnecessary git changes and respecting individual developer workflow choices.

### Local Markdown Preview Setup (Optional)

To enable GitHub-like table rendering in VS Code Markdown Preview for this workspace:

1. Open VS Code **User Settings** (Ctrl+Shift+P → "Preferences: Open User Settings (JSON)").
2. Add the following snippet to `~/.config/Code/User/settings.json`:
   ```json
   "markdown.preview.fontFamily": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif",
   "markdown.preview.lineHeight": 1.6,
   "markdown.preview.typographer": false,
   "markdown.preview.scrollPreviewWithEditor": true,
   "markdown.preview.scrollEditorWithPreview": true,
   "markdown.preview.doubleClickToSwitchToEditor": true
   ```
3. (Optional) Install the recommended extension: **GitHub Markdown Preview** (bierner.github-markdown-preview).
4. Open any `.md` file and press **Ctrl+Shift+V** (Markdown Preview) or **Ctrl+K, V** (Preview to the side).

This setup remains local to your VS Code profile and does not appear in `git status`.

## D-2026-05-11-007

- Date: 2026-05-11
- Related task: T-2026-05-11-010 (scope planning for prompt manifest and governance)
- Decision: Recommended VS Code extensions for this project are listed in `.vscode/extensions.json` to guide contributors toward a consistent developer experience.
- Decision: All extensions listed are for productivity, code quality, or collaboration only. No extension is required to run or test code; all are optional tools to enhance local workflow.
- Rationale: VS Code's extension recommendation system allows contributors to adopt a standard toolchain with one click ("Install All Recommended") without enforcing mandatory installation. This balances team consistency with individual choice.