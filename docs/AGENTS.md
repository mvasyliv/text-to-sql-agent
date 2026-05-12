# Project Agents Guide

This document explains how to use the specialized GitHub Copilot agents in the text-to-sql-agent project.

## Specialized Agents

We have 5 specialized agents, each with distinct responsibilities and constraints:

### 1. **Architect Agent** (`.architect.instructions.md`)
**Use when:** Designing system architecture, reviewing design, analyzing dependencies
**Responsibilities:**
- Design new features and system components
- Review architectural consistency
- Propose refactoring and structural improvements
- Update `docs/ARCHITECTURE.md`
- Document decisions in `docs/DECISIONS.md`

**How to activate:**
- Ask: "As the architect, please design..."
- Or reference: "@architect-agent"

---

### 2. **Task Manager Agent** (`.taskmanager.instructions.md`)
**Use when:** Creating tasks, planning work, organizing sprints
**Responsibilities:**
- Create new tasks in `docs/TASKS.md`
- Break down features into sub-tasks
- Estimate effort and prioritize
- Track task status and progress
- Update `docs/WORKLOG.md`

**How to activate:**
- Ask: "As the task manager, please create a task for..."
- Or reference: "@task-manager"

---

### 3. **Developer Agent** (`.developer.instructions.md`)
**Use when:** Writing code, implementing features, refactoring
**Responsibilities:**
- Implement features from tasks
- Write clean, type-hinted Python code
- Follow project conventions
- Create/update modules
- Use proper Git workflow (feature branches, commits)

**How to activate:**
- Ask: "As the developer, please implement..."
- Or reference: "@developer"

---

### 4. **Tester/QA Agent** (`.tester.instructions.md`)
**Use when:** Writing tests, validating code, ensuring quality
**Responsibilities:**
- Write unit and integration tests
- Test edge cases and error conditions
- Run linting and type checking
- Verify acceptance criteria
- Maintain test coverage (80%+)
- Keep tests in mirrored package layout (`tests/text_to_sql_agent/<package>/...`)

**How to activate:**
- Ask: "As the tester, please write tests for..."
- Or reference: "@tester"

---

### 5. **Documentarian Agent** (`.documentarian.instructions.md`)
**Use when:** Writing documentation, updating guides, explaining features
**Responsibilities:**
- Update `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, `docs/CHANGELOG.md`
- Write README sections
- Document APIs and usage
- Create diagrams (Mermaid)
- Maintain documentation quality

**How to activate:**
- Ask: "As the documentarian, please document..."
- Or reference: "@documentarian"

---

## Typical Workflow Using Agents

### Phase 1: Planning (Architect + Task Manager)
1. **Architect** designs the feature architecture
   - Proposes component design
   - Documents in `docs/ARCHITECTURE.md`
   - Saves decision in `docs/DECISIONS.md`

2. **Task Manager** creates tasks
   - Breaks down feature into implementation steps
   - Creates entries in `docs/TASKS.md`
   - Identifies dependencies

### Phase 2: Implementation (Developer + Tester)
3. **Developer** implements feature
   - Follows architecture design
   - Creates feature branch
   - Writes code with type hints
   - Commits with proper message format

4. **Tester** validates implementation
   - Writes comprehensive tests
   - Verifies acceptance criteria
   - Runs linting and type checks
   - Reports coverage

### Phase 3: Documentation (Documentarian)
5. **Documentarian** documents the work
   - Updates `docs/WORKLOG.md` with implementation details
   - Adds diagrams to `docs/ARCHITECTURE.md` if needed
   - Updates `docs/CHANGELOG.md`
   - Ensures README examples are correct

---

## Example Prompts

### To Architect
```
"@architect: Design how to integrate Redis caching for query results. 
Consider performance trade-offs and show the integration points with existing components."
```

### To Task Manager
```
"@task-manager: Create a task breakdown for implementing PostgreSQL support. 
Include connection pooling, query execution, and error handling."
```

### To Developer
```
"@developer: Implement the PostgreSQL database driver following the architecture design. 
Include connection pooling and type hints. Create the feature branch and commit with proper format."
```

### To Tester
```
"@tester: Write comprehensive tests for the PostgreSQL driver. 
Test connection pooling, timeouts, invalid credentials, and query execution. 
Target 85%+ coverage."
```

### To Documentarian
```
"@documentarian: Update docs/WORKLOG.md with implementation details from T-2026-05-11-009. 
Add a diagram showing PostgreSQL integration to ARCHITECTURE.md."
```

---

## Agent Coordination

When multiple agents work together:

1. **Architect → Task Manager**: "Here's the design; please break it into tasks"
2. **Task Manager → Developer**: "Here are the tasks to implement"
3. **Developer → Tester**: "I've implemented this; please test it"
4. **Tester → Developer**: "Tests found these issues; please fix"
5. **All → Documentarian**: "Please document what we've done"

---

## Constraints & Rules

All agents follow:
- **English only** for code, comments, and documentation
- **Project structure**: Keep code under `src/text_to_sql_agent/`
- **Git workflow**: Feature branches, no direct commits to main
- **Type hints**: Mandatory for all Python code
- **Configuration**: Via `.env*` files, no hardcoded secrets
- **Logging**: Use loguru via config module
- **Testing**: 80%+ coverage target

---

## Quick Reference

| Agent | Files to Update | Key Constraints | Trigger Phrase |
| --- | --- | --- | --- |
| Architect | ARCHITECTURE.md, DECISIONS.md | Design only, no implementation | "@architect" |
| Task Manager | TASKS.md, WORKLOG.md | Task format (T-YYYY-MM-DD-###) | "@task-manager" |
| Developer | src/, pyproject.toml, uv.lock | Type hints, English, feature branches | "@developer" |
| Tester | tests/, pytest config | 80%+ coverage, deterministic | "@tester" |
| Documentarian | docs/, README.md | English, Markdown, Mermaid diagrams | "@documentarian" |

---

## Enabling Agents in VS Code

To use agents in VS Code Copilot:

1. Open the file or folder related to your task
2. Open Copilot Chat (Ctrl+Shift+I or Cmd+Shift+I)
3. Type your prompt with agent reference: `@architect`, `@developer`, etc.
4. Copilot will apply the relevant instructions

Alternatively, if your VS Code version supports agent selection:
1. In Copilot Chat, look for agent selector dropdown
2. Choose: Architect, Task Manager, Developer, Tester, or Documentarian
3. Type your prompt

---

## Notes

- Agents are **complementary**, not competitive
- Each agent has a specific expertise and scope
- Using the right agent for the right task **improves quality and speed**
- Agent instructions are stored as `.*.instructions.md` files in the project root
- Agents inherit base rules from `.github/copilot-instructions.md`
