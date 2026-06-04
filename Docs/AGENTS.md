# AGENTS.md — Hive

## Before starting

Read `Docs/DESIGN.md` first — it's the authoritative source for architecture, agent system, data model, and all task definitions.

## Project state

Greenfield. Only `Docs/DESIGN.md` exists. All code must be written from scratch following the task breakdown in that doc.

## Key facts

- **Stack**: Python ≥3.11, Textual, LangGraph, LiteLLM, httpx, SQLite
- **Package manager**: `uv` only (no pip/poetry). Use `uv add`, `uv sync`, `uv run`.
- **Entry point**: `hive.main:main` (registered as `[project.scripts].hive` in `pyproject.toml`)
- **Test runner**: pytest in `tests/`
- **Config**: TOML, stored in OS config dir via `platformdirs` — never in the repo
- **Core constraint**: `hive/core/` must have zero Textual imports — testable independently
- **Orchestration**: LangGraph `StateGraph` with `SqliteSaver` checkpointer
- **API keys**: user-supplied via TUI, written to `os.environ` before LiteLLM calls
- **Supported providers**: OpenAI, Anthropic, Google Gemini, Groq, Ollama (local)
- **Export**: Markdown via `markdown` lib, PDF via `weasyprint`

## Commands

```bash
uv sync                    # install all deps
uv run pytest              # run all tests
uv run hive                # run the app
uv build                   # build for PyPI
uv publish                 # publish to PyPI
```

## Task conventions

- Implement tasks in order per the `Docs/DESIGN.md` phase/task breakdown.
- Every completed task gets a `CHANGELOG.md` entry under `[Unreleased]` following Keep a Changelog format — user-facing, one line, prefixed with task ID e.g. `[TASK-001] Added project scaffold`.
- Version bumps per SemVer on release (minor for features, patch for fixes).

## File layout

```
hive/main.py                 — entry point
hive/core/                   — no Textual imports
hive/core/graph/             — LangGraph state + graph + router
hive/core/nodes/             — planner, browser, researcher, synthesizer, critic
hive/core/tools/             — search, scraper, citations
hive/tui/                    — Textual screens + widgets + styles
hive/db/sessions.py          — SQLite + LangGraph checkpoint store
hive/export/                 — markdown.py, pdf.py
tests/                       — pytest tests per module
```
