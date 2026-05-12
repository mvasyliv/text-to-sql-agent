# Contributing to text-to-sql-agent

## Branch Strategy (GitHub Flow)

`main` is always stable and deployable. All work happens on feature branches.

```
main  (protected — merge via PR only)
  └── feature/<short-description>
  └── fix/<short-description>
  └── chore/<short-description>
```

### Rules

- Never push directly to `main`.
- Branch off from the latest `main`:
  ```bash
  git checkout main && git pull origin main
  git checkout -b feature/your-feature-name
  ```
- Keep branches focused on a single task or fix.
- Delete the branch after the PR is merged.

## Pull Request Process

1. Push your branch to `origin`:
   ```bash
   git push -u origin feature/your-feature-name
   ```
2. Open a Pull Request on GitHub targeting `main`.
3. Wait for review and approval from the repository owner before merging.
4. Squash or merge commits as agreed with the reviewer.

## Branch Protection on `main`

`main` is protected:
- Direct pushes are blocked.
- At least one approving review is required before merging.
- All status checks (CI, linting) must pass.

## Commit Style

Use the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <short description> [<task-id>]
```

Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`.

Example:
```
feat(prompts): add evaluation gate contracts [T-2026-05-11-016]
```

## Development Setup

```bash
git clone git@github.com:mvasyliv/text-to-sql-agent.git
cd text-to-sql-agent
uv sync
source venvtext2sql/bin/activate
```

Run tests:
```bash
uv run pytest -q
```

Run linting:
```bash
uv run ruff check src tests
```

## Task Tracking

All tasks are recorded in [docs/TASKS.md](docs/TASKS.md).  
Implementation history is kept in [docs/WORKLOG.md](docs/WORKLOG.md).  
Architecture decisions are in [docs/DECISIONS.md](docs/DECISIONS.md).
