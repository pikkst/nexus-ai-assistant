# Nexus Local AI Assistant — Rules & Conventions

> **Version:** 1.0.0  
> **Language:** English  
> **Purpose:** Operational rules that all agents must follow when working on the Nexus project.

---

## 1. Golden Rule

**Every task = new branch → implement → update memory → update task → PR → merge**

This sequence is mandatory. No exceptions. Skipping any step is a violation.

---

## 2. Branch Rules

### 2.1 Branch Naming

| Branch Type | Pattern | Example |
|------------|---------|---------|
| Main | `main` | `main` |
| Integration | `develop` | `develop` |
| Feature | `feature/<short-description>` | `feature/audio-capture-service` |
| Bug Fix | `fix/<short-description>` | `fix/vad-crash-on-silence` |
| Documentation | `docs/<short-description>` | `docs/api-contracts` |
| Hotfix | `hotfix/<short-description>` | `hotfix/crash-on-startup` |

### 2.2 Branch Lifecycle

```
1. Start from develop:
   git checkout develop
   git pull
   git checkout -b feature/my-task

2. Do work, commit regularly:
   git add <files>
   git commit -m "descriptive message"

3. Push and create PR:
   git push -u origin feature/my-task
   # Create PR on GitHub/GitLab

4. After PR is merged:
   git checkout develop
   git pull
   git branch -d feature/my-task
```

### 2.3 Commit Messages

Use conventional commits:

```
feat: add audio capture service
fix: correct VAD silence threshold
docs: update tehnika.md with API spec
refactor: extract VAD into separate module
test: add audio capture unit tests
chore: update dependencies
style: fix indentation in capture.py
```

Format: `<type>: <imperative description>`

---

## 3. Pull Request Rules

### 3.1 PR Template

```markdown
## Description
[What does this PR do?]

## Related Task
[Link to task in task.md]

## Changes
- [Change 1]
- [Change 2]

## How to Test
1. [Step 1]
2. [Step 2]
3. [Expected result]

## Checklist
- [ ] Code follows coding standards (agents.md §5)
- [ ] Tests pass (`pytest tests/ -v`)
- [ ] Type checks pass (`mypy src/`)
- [ ] memory.md updated with decisions/blockers
- [ ] task.md updated (status changed)
- [ ] Self-reviewed before opening
```

### 3.2 PR Requirements

1. **Title** must be clear and descriptive
2. **Description** must link to the task in `task.md`
3. **Do not merge** until:
   - All Acceptance Criteria are met
   - All tests pass
   - Type checks pass
   - `memory.md` and `task.md` are updated
4. **Review** by at least one other agent (simulated or human)
5. **Squash merge** preferred to keep history clean

---

## 4. Memory Update Rules

### 4.1 When to Update memory.md

You **MUST** update `memory.md` when:

- You complete a task → update Project State table
- You make a technical decision → add to Decision Log
- You encounter a blocker → add to Blocker Log
- You change an API contract → update API Contracts Summary
- You discover something important future agents should know → add to Current Sprint Context

### 4.2 What to Write

- **Project State:** Change status from 📋 Planned → ⏳ In Progress → ✅ Done
- **Decision Log:** Add row with ID, date, decision, rationale, author
- **Blocker Log:** Add row with ID, date, blocker description, status, resolution
- **Current Sprint Context:** Update what is being built, files modified, known issues, next task

---

## 5. Task Update Rules

### 5.1 When to Update task.md

You **MUST** update `task.md` when:

- You start a task → change status to ⏳ IN PROGRESS
- You complete a task → change status to ✅ DONE, add to Completed Tasks table
- You discover a new task needed → add new entry with full format
- A task is blocked → add blocker note under the task

### 5.2 Task Format (Mandatory)

Every task entry **MUST** follow this exact structure:

```markdown
### Task: TASK-ID — Short Name

**Status:** ⏳ IN PROGRESS | 📋 BACKLOG | ✅ DONE | 🚫 BLOCKED

---

## Task Description

[Clear description of what needs to be built]

## User Story

As a [role],
I need [capability]
so that [benefit]

## Acceptance Criteria

- [ ] **AC-1:** [criterion description]
- [ ] **AC-2:** [criterion description]
- [ ] **AC-3:** [etc.]

## Definition of Done

- [Concrete verification steps]
- [e.g., "Tests pass", "PR merged", "Feature works end-to-end"]

---

**EST:** X SP

**RT:** YYYY-MM-DD
**QA:** YYYY-MM-DD
```

---

## 6. File Change Protocol

1. **Always read** a file before modifying it
2. **One change at a time** — never batch unrelated changes
3. **Verify syntax** after every write (Python: `python -c "import ast; ast.parse(open('file.py').read())"`)
4. **If a change breaks something**, revert immediately and log in memory.md why it broke
5. **Never overwrite** another agent's work without coordination (check `memory.md` first)
6. **Use `pathlib`** for all file paths (no `os.path`)
7. **Keep files under 150 lines** — if a file is larger, split it

---

## 7. Testing Rules

1. **Every module must have tests** — no untested code in `develop`
2. **Run tests before opening a PR** — `pytest tests/ -v` must pass
3. **Minimum 80% code coverage** for new code
4. **Mock hardware** in CI — never require real camera/mic for tests
5. **Test error paths** — what happens when a device is missing, a model fails to load, etc.
6. **Async tests** — use `pytest-asyncio` with `@pytest.mark.asyncio`

---

## 8. Code Review Rules

1. **Read every line** of the diff
2. **Check for**:
   - Correctness (does the code do what the task says?)
   - Style (does it match agents.md §5?)
   - Edge cases (what happens when input is empty, device missing, etc.?)
   - Security (no command injection, no data leaks, no hardcoded secrets)
   - Performance (no unnecessary copies, no blocking calls in async code)
3. **Approve only** when you're satisfied the code is correct and complete
4. **Request changes** with specific, actionable feedback

---

## 9. Error Handling Rules

1. **Never swallow exceptions** — no bare `except:` or `except Exception: pass`
2. **Always log** the error before handling it: `logger.error("Failed to X: {e}")`
3. **Graceful degradation** — if a module fails, the rest of the app continues
4. **User-facing errors** must be in the user's language (English for now)
5. **Retry transient failures** (device busy, network timeouts) once with backoff

---

## 10. Conventions

### 10.1 Python
- Use `ruff` for linting and formatting
- Sort imports with `isort`
- Type hints on every function signature
- Google-style docstrings
- `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_CASE` for constants
- Use `from __future__ import annotations` at top of every file

### 10.2 File Organization
- One class per file (except small helper classes)
- One export per module (the main class); helpers are private (prefixed with `_`)
- `__init__.py` re-exports the public API

### 10.3 Documentation
- All documentation in English
- Version number and last-updated date in every document
- Markdown format for all docs
- ASCII art for diagrams (no external tools)

---

## 11. Package Management

1. All dependencies pinned in `requirements.txt` with minimum version
2. Development dependencies in `requirements-dev.txt`
3. Use `pip` for package management (no poetry/conda unless consensus)
4. Run `pip install -r requirements.txt` before starting work
5. When adding a dependency, update both `requirements.txt` and `pyproject.toml`

---

## 12. Communication Rules

1. **Read first, ask second** — always read the relevant docs before asking for help
2. **Be specific** — "I got error X when running Y" not "it doesn't work"
3. **Log blockers** in `memory.md` and `task.md` — don't just wait silently
4. **If you break something**, say so immediately and revert or fix

---

## 13. Violation Consequences

| Violation | Consequence |
|-----------|-------------|
| Skipping memory.md update | PR rejected until updated |
| Direct push to main/develop | Branch reverted, task reassigned |
| Merging without review | PR reverted, agent must redo |
| Untested code in develop | Immediate revert |
| Ignoring file change protocol | Code reverted, agent must redo |

---

> **Last updated:** 2026-07-12  
> **Maintainer:** Documentation Agent
