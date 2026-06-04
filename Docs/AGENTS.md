# AGENTS.md — research-assistant

**This repo is pre-implementation.** The single source of truth is `Docs/DESIGN.md`. Nothing has been built yet — all code, config, and tests are absent.

## Package identity

- PyPI name: `research-assistant`, entry point: `research_assistant.main:main`
- Python 3.11+, package manager: `uv`
- Dependencies in `pyproject.toml` (see DESIGN.md for full list)

## Architecture constraint

The `core/` layer must have **zero Textual imports** — it is designed to be testable independently and potentially reused as a library or REST API.

## Development workflow

- Work is organized as numbered tasks (`TASK-001` through `TASK-030`) in DESIGN.md
- `CHANGELOG.md` must be maintained per the rules in DESIGN.md (Keep a Changelog, SemVer, task IDs in entries)
- Version bumps: feature task → minor, bug/polish → patch, breaking API/config change → major

## Relevant files

| File | Purpose |
|------|---------|
| `Docs/DESIGN.md` | Full design, architecture, task breakdown |
| `CHANGELOG.md` | Must exist at root, maintained per DESIGN.md rules |
| `pyproject.toml` | Does not exist yet — create with `uv init` |
