# Changelog

All notable changes to hive are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [SemVer](https://semver.org/)

## [Unreleased]

### Fixed

- [TASK-006] Settings screen no longer crashes when saved model is not in fallback model list

### Added

- [TASK-020] Research screen assembling all widgets with async graph streaming and cancellation
- [TASK-019] Status bar widget showing model name, token usage, and estimated cost
- [TASK-018] Citations widget with clickable numbered badges opening URLs in browser
- [TASK-017] Chat widget with real-time streaming token display and Markdown rendering via rich
- [TASK-016] Agent panel widget with status tree driven by LangGraph astream_events
- [TASK-015] Critic node that reviews synthesis quality and triggers replan loop via conditional routing
- [TASK-014] Synthesizer node that composes research notes into a coherent cited final answer
- [TASK-013] Researcher node that extracts facts from sources with inline citation tracking via LLM
- [TASK-012] Browser node that searches and scrapes top results in parallel via LangGraph Send API
- [TASK-011] Planner node that breaks queries into sub-queries via LLM with JSON parsing and fallback plan
- [TASK-010] LangGraph pipeline scaffold with HiveState, stub nodes, and SqliteSaver checkpointing
- [TASK-009] Citation tracker with incremental indexing and Markdown reference formatting
- [TASK-008] Web scraper tool with async httpx fetching and readability-lxml extraction
- [TASK-001] Project scaffold with pyproject.toml, directory structure, and entry point
- [TASK-002] Config system with load, save, apply, and key masking
- [TASK-003] LiteLLM wrapper with streaming, completion, and model listing
- [TASK-004] Textual app skeleton with screen routing, config check, and keybindings
- [TASK-005] Setup wizard with provider inputs, model selector, and config save
- [TASK-006] Settings screen with masked pre-filled values, Save, and Cancel
- [TASK-007] Search tool with Tavily and DuckDuckGo fallback
- Models fetched dynamically from provider APIs (OpenAI, Groq, Google, Ollama) with fallback lists

## [0.1.0] — YYYY-MM-DD

### Added

- Initial project scaffold
