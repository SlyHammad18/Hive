# Research Assistant — Design Document

> A multi-agent research assistant TUI. Users bring their own API keys.
> Built with Python + Textual + LangGraph. Published to PyPI.

---

## Table of Contents

1. [Overview](#overview)
2. [Goals & Non-Goals](#goals--non-goals)
3. [Architecture](#architecture)
4. [Agent System](#agent-system)
5. [TUI Layout](#tui-layout)
6. [Provider & Key Management](#provider--key-management)
7. [Data Model](#data-model)
8. [Export System](#export-system)
9. [Tech Stack](#tech-stack)
10. [Project Structure](#project-structure)
11. [Task Breakdown](#task-breakdown)
12. [Changelog Instructions](#changelog-instructions)

---

## Overview

`hive` is a terminal UI application that lets users run deep, multi-agent
research queries against any major AI provider. A query fans out to a small
team of specialized agents — one browses the web, one extracts and reads
sources, one synthesizes findings, and one critiques the output. The agent
pipeline is orchestrated by LangGraph, giving the system checkpointing,
resumable runs, and clean conditional routing between nodes.

Results include tracked citations and can be exported to Markdown or PDF.
Users supply their own API keys for OpenAI, Anthropic, Google Gemini, and/or
Ollama. Keys are stored locally in the OS config directory and managed
entirely through the TUI — no manual file editing required.

---

## Goals & Non-Goals

### Goals

- Clean, minimal TUI that feels fast and native in any terminal
- Multi-agent pipeline with live status visibility
- Support for OpenAI, Anthropic, Google Gemini, and Ollama (local)
- Web search and page reading per query
- Citation tracking — every claim traceable to a source URL
- Export to Markdown and PDF
- First-run setup wizard for API keys
- Session history with SQLite persistence
- Cost and token tracking per session

### Non-Goals

- No hosted backend — the app is fully local
- No user accounts or cloud sync
- No GUI or web interface
- No support for image/multimodal queries in v1
- No real-time collaborative sessions

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Textual TUI                       │
│  ┌──────────────┐  ┌───────────────────────────────┐│
│  │  Agent Panel │  │       Chat / Output            ││
│  │              │  │                                ││
│  │ ● Orchestrat.│  │  streaming response tokens     ││
│  │   ├ Browser ✓│  │                                ││
│  │   ├ Researcher│  │                                ││
│  │   └ Synthes. │  │                                ││
│  └──────────────┘  └───────────────────────────────┘│
│  ┌────────────────────────────────────────────────┐ │
│  │  Citations bar          [1] [2] [3] ...        │ │
│  └────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────┐ │
│  │  > _                         [export]  [new]   │ │
│  └────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
         │                        │
         ▼                        ▼
   LangGraph pipeline        SQLite (sessions,
   (StateGraph + nodes)       citations, history)
         │
         ▼
   LiteLLM layer
 (OpenAI / Anthropic /
  Gemini / Ollama)
         │
         ▼
   Tavily / DDG search
   httpx + readability
```

The TUI layer is purely presentational. All business logic lives in `core/`.
The `core/` layer has no Textual imports — it can be tested independently
and later exposed as a library or REST API if needed.

The LangGraph `StateGraph` is the execution engine for the entire agent
pipeline. The TUI subscribes to LangGraph's event stream to update the
agent panel and chat widget in real time as nodes execute.

---

## Agent System

### Roles

| Agent | LangGraph Node | Responsibility |
|---|---|---|
| Planner | `plan` | Parses the query, produces a list of 2–4 sub-queries, writes the plan into graph state |
| Browser | `browse` | Runs web searches and scrapes pages for each sub-query; runs as a parallel fan-out |
| Researcher | `research` | Reads all browser output, extracts key facts and quotes, tags citations |
| Synthesizer | `synthesize` | Merges researcher notes into a coherent, well-structured answer |
| Critic | `critique` | Reviews synthesis for gaps and weak citations; conditionally loops back to `plan` if quality is too low |

### LangGraph State

All nodes read from and write to a single typed state object:

```python
from typing import Annotated
from langgraph.graph import add_messages

class HiveState(TypedDict):
    query: str                          # original user query
    plan: list[str]                     # sub-queries from planner
    browser_results: list[BrowserResult]
    research_notes: str
    synthesis: str
    critique: CritiqueResult
    citations: list[Citation]
    token_usage: TokenUsage
    iteration: int                      # tracks critique → replan loops
    messages: Annotated[list, add_messages]
```

### Graph Definition

```python
from langgraph.graph import StateGraph, END

graph = StateGraph(HiveState)

graph.add_node("plan",      planner_node)
graph.add_node("browse",    browser_node)      # fan-out via Send API
graph.add_node("research",  researcher_node)
graph.add_node("synthesize", synthesizer_node)
graph.add_node("critique",  critic_node)

graph.set_entry_point("plan")
graph.add_edge("plan",      "browse")
graph.add_edge("browse",    "research")
graph.add_edge("research",  "synthesize")
graph.add_edge("synthesize","critique")

# Conditional edge: critic decides whether to loop or finish
graph.add_conditional_edges(
    "critique",
    should_continue,            # returns "plan" or END
    {"plan": "plan", END: END}
)

app = graph.compile(checkpointer=SqliteSaver(conn))
```

### Execution Flow

```
User query
    │
    ▼
┌─────────┐     ┌──────────────────────────────┐
│  plan   │────▶│  browse (parallel via Send)  │
│  node   │     │  browser×N running at once   │
└─────────┘     └──────────────┬───────────────┘
                               │
                    ┌──────────▼──────────┐
                    │    research node    │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │   synthesize node   │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │    critique node    │
                    └──────┬──────┬───────┘
                           │      │
                    quality OK   too weak (max 2 loops)
                           │      │
                          END   back to plan
```

### Parallel Browsing via Send API

LangGraph's `Send` API fans out browser nodes in parallel — one per
sub-query — without manual `asyncio.gather()`:

```python
from langgraph.constants import Send

def plan_to_browse(state: HiveState):
    return [Send("browse", {"sub_query": q}) for q in state["plan"]]

graph.add_conditional_edges("plan", plan_to_browse)
```

Each browser node runs concurrently and writes its result back into
`browser_results` in the shared state.

### Checkpointing & Resumability

The graph is compiled with `SqliteSaver` as the checkpointer. Every node
transition is persisted. If a run fails mid-pipeline, it can be resumed
from the last completed node rather than restarting from scratch. The
same checkpoint store also powers session history in the TUI.

```python
from langgraph.checkpoint.sqlite import SqliteSaver

conn = get_db_connection()   # from db/sessions.py
app = graph.compile(checkpointer=SqliteSaver(conn))

# Run with a thread_id — each session is a unique thread
config = {"configurable": {"thread_id": session_id}}
async for event in app.astream({"query": user_query}, config=config):
    yield event   # streamed to TUI
```

### Streaming to the TUI

LangGraph's `astream_events` emits fine-grained events as each node
runs. The TUI subscribes to this stream and updates reactively:

```python
async for event in app.astream_events(input, config, version="v2"):
    kind = event["event"]
    if kind == "on_chain_start":
        tui.set_agent_status(event["name"], "running")
    elif kind == "on_chat_model_stream":
        tui.append_token(event["data"]["chunk"].content)
    elif kind == "on_chain_end":
        tui.set_agent_status(event["name"], "done")
```

Each agent's status in the agent panel transitions through:
`◌ waiting → ↻ running → ✓ done / ✗ error`.

---

## TUI Layout

### Screens

| Screen | Trigger | Description |
|---|---|---|
| Setup Wizard | First launch, no config | API key entry form |
| Home | Default on launch | New session or resume history |
| Research | After submitting a query | Main workspace |
| Settings | `s` key or menu | Manage API keys and model defaults |
| History | `h` key or menu | Past sessions list with search |

### Research Screen Panels

```
┌─ Header ─────────────────────────────────────────────────────┐
│  research-assistant    claude-sonnet-4-6   1,240 tok   $0.02 │
├─ Left (30%) ─────────────┬─ Right (70%) ────────────────────┤
│                          │                                    │
│  AGENTS                  │  OUTPUT                            │
│                          │                                    │
│  ◉ Orchestrator          │  [streaming markdown content]      │
│    ├ ✓ Browser           │                                    │
│    ├ ↻ Researcher        │                                    │
│    └ ◌ Synthesizer       │                                    │
│                          │                                    │
│  ──────────────          │                                    │
│  CITATIONS               │                                    │
│  [1] Title — site.com    │                                    │
│  [2] Title — other.org   │                                    │
│                          │                                    │
├──────────────────────────┴────────────────────────────────────┤
│  > _                                         [⎘ export] [+ new]│
└───────────────────────────────────────────────────────────────┘
```

### Keyboard Shortcuts

| Key | Action |
|---|---|
| `Enter` | Submit query |
| `s` | Open settings |
| `h` | Open history |
| `e` | Export current session |
| `n` | New session |
| `q` | Quit |
| `Ctrl+C` | Cancel running query |
| `↑ / ↓` | Scroll output |
| `Tab` | Cycle between panels |

---

## Provider & Key Management

### Config Location

Keys are stored in the OS-standard config directory, never in the
project folder or version control:

```
Windows:   %APPDATA%\research-assistant\config.toml
macOS:     ~/Library/Application Support/research-assistant/config.toml
Linux:     ~/.config/research-assistant/config.toml
```

### Config Schema

```toml
[providers]
openai_api_key     = ""
anthropic_api_key  = ""
google_api_key     = ""
ollama_base_url    = "http://localhost:11434"

[defaults]
provider  = "anthropic"
model     = "claude-sonnet-4-6"
max_tokens = 4096

[search]
tavily_api_key = ""
fallback       = "duckduckgo"   # used if tavily key is empty
max_results    = 8

[export]
output_dir = "~/research-exports"
```

### First-Run Wizard

On launch with no config file, the app enters a setup wizard screen:

1. Welcome message explaining local key storage
2. Input fields for each provider (all optional except at least one)
3. Model selector (auto-populated based on which keys were entered)
4. Tavily API key (optional — DDG is the fallback)
5. Save & Continue button

Keys are masked in the input fields (`sk-ant-••••••••`) after entry.
The Settings screen replicates the same form for later updates.

### Runtime Injection

Keys are loaded once at startup and written to `os.environ` before any
LiteLLM call. They are never passed directly in API call arguments.

---

## Data Model

### Session

```python
@dataclass
class Session:
    id: str                    # UUID
    created_at: datetime
    query: str                 # Original user query
    provider: str
    model: str
    messages: list[Message]
    citations: list[Citation]
    token_usage: TokenUsage
    cost_usd: float
```

### Citation

```python
@dataclass
class Citation:
    index: int                 # [1], [2], ... as shown in output
    url: str
    title: str
    snippet: str               # Relevant excerpt (max 300 chars)
    agent: str                 # Which agent tagged this
    timestamp: datetime
```

### Message

```python
@dataclass
class Message:
    role: str                  # "user" | "assistant" | "agent"
    agent_name: str | None     # e.g. "Researcher"
    content: str
    timestamp: datetime
```

### Storage

SQLite via stdlib `sqlite3`. Three tables: `sessions`, `messages`,
`citations`. All writes are async-safe via a single write queue.
The DB file lives alongside `config.toml` in the OS config dir.

---

## Export System

### Markdown Export

Renders the full synthesis with:
- Session metadata header (date, model, query)
- Full output with citation markers inline
- Numbered references section at the bottom
- Agent trace (collapsible in Markdown via `<details>`)

Output filename: `research-YYYY-MM-DD-HH-MM.md`

### PDF Export

Converts the Markdown export to PDF via `weasyprint`. Applies a
minimal stylesheet — clean whitespace, monospace code blocks,
linked footnotes for citations.

Output filename: `research-YYYY-MM-DD-HH-MM.pdf`

Both are saved to the `export.output_dir` from config (default:
`~/research-exports`). The TUI shows a confirmation with the file path
after export completes.

---

## Tech Stack

| Component | Library | Reason |
|---|---|---|
| TUI framework | `textual >= 0.60` | Best Python TUI; async-native; CSS styling |
| Agent orchestration | `langgraph >= 0.2` | State graph, parallel fan-out, checkpointing, conditional loops |
| AI providers | `litellm >= 1.40` | Single interface for all 4 providers |
| LLM base | `langchain-core` | Required by LangGraph; provides message types and streaming |
| Web search | `tavily-python` | Research-optimized results |
| Search fallback | `duckduckgo-search` | No API key needed |
| HTTP client | `httpx` | Async-first; used for scraping |
| HTML extraction | `readability-lxml` | Clean article text from any page |
| PDF export | `weasyprint` | Markdown → PDF with CSS control |
| Markdown render | `markdown` + `rich` | In-TUI rendering and export |
| Config files | `tomli-w` + `tomllib` | TOML read/write for config |
| Config paths | `platformdirs` | OS-correct config/data directories |
| Checkpointing | `langgraph-checkpoint-sqlite` | Persists graph state to SQLite |
| Package manager | `uv` | Fast, modern Python tooling |
| Distribution | PyPI | Primary install channel |

### Python Version

3.11+ required (uses `tomllib` from stdlib, `asyncio.TaskGroup`).

### Dependencies (`pyproject.toml`)

```toml
[project]
name = "hive"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "textual>=0.60",
    "langgraph>=0.2",
    "langgraph-checkpoint-sqlite",
    "langchain-core",
    "litellm>=1.40",
    "tavily-python",
    "duckduckgo-search",
    "httpx",
    "readability-lxml",
    "weasyprint",
    "markdown",
    "rich",
    "platformdirs",
    "tomli-w",
]

[project.scripts]
hive = "hive.main:main"
```

---

## Project Structure

```
hive/
│
├── pyproject.toml
├── README.md
├── CHANGELOG.md                  ← maintained per instructions below
│
├── hive/
│   ├── __init__.py
│   ├── main.py                   # Entry point: load config → launch TUI
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py             # Load/save config.toml, apply keys to env
│   │   ├── llm.py                # LiteLLM wrapper: stream(), complete()
│   │   │
│   │   ├── graph/
│   │   │   ├── __init__.py
│   │   │   ├── state.py          # HiveState TypedDict definition
│   │   │   ├── graph.py          # StateGraph definition, compile(), edges
│   │   │   └── router.py         # should_continue() conditional edge logic
│   │   │
│   │   ├── nodes/
│   │   │   ├── __init__.py
│   │   │   ├── planner.py        # plan node: breaks query into sub-queries
│   │   │   ├── browser.py        # browse node: search + scrape
│   │   │   ├── researcher.py     # research node: extract facts + citations
│   │   │   ├── synthesizer.py    # synthesize node: write final answer
│   │   │   └── critic.py         # critique node: review + conditional loop
│   │   │
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── search.py         # Tavily + DDG fallback
│   │       ├── scraper.py        # httpx + readability
│   │       └── citations.py      # Citation tracker
│   │
│   ├── tui/
│   │   ├── __init__.py
│   │   ├── app.py                # Textual App root, screen router
│   │   │
│   │   ├── screens/
│   │   │   ├── setup.py          # First-run wizard
│   │   │   ├── home.py           # Landing screen
│   │   │   ├── research.py       # Main workspace
│   │   │   ├── settings.py       # API key management
│   │   │   └── history.py        # Past sessions
│   │   │
│   │   ├── widgets/
│   │   │   ├── agent_panel.py    # Graph node status tree
│   │   │   ├── chat.py           # Streaming message thread
│   │   │   ├── citations.py      # Citation sidebar
│   │   │   └── statusbar.py      # Model / token / cost
│   │   │
│   │   └── styles/
│   │       └── main.tcss         # Textual CSS — clean minimal theme
│   │
│   ├── export/
│   │   ├── __init__.py
│   │   ├── markdown.py
│   │   └── pdf.py
│   │
│   └── db/
│       ├── __init__.py
│       └── sessions.py           # SQLite: sessions, messages, citations
│                                 # also used as LangGraph checkpoint store
│
└── tests/
    ├── test_config.py
    ├── test_graph.py
    ├── test_nodes.py
    ├── test_search.py
    └── test_export.py
```

---

## Task Breakdown

Tasks are ordered by dependency. Each task is self-contained and
shippable. Complete them in sequence within each phase.

---

### Phase 1 — Foundation

#### TASK-001 — Project scaffold
- Init repo with `uv init`
- Write `pyproject.toml` with all dependencies and the `research-assistant` entry point
- Create folder structure as defined above
- Add `.gitignore`, `README.md`, `CHANGELOG.md` (empty, with format instructions)
- Set up `tests/` with pytest
- **Done when:** `uv run research-assistant` runs without error (even if it just prints a message)

#### TASK-002 — Config system
- Implement `core/config.py`:
  - `load_config()` — reads `config.toml` from platformdirs path; returns empty dict if missing
  - `save_config(data)` — writes to platformdirs path, creates dir if needed
  - `apply_config(config)` — writes keys to `os.environ` for LiteLLM
  - `mask_key(key)` — returns `sk-ant-••••••••` style string for display
- **Done when:** config round-trips correctly in a unit test

#### TASK-003 — LiteLLM wrapper
- Implement `core/llm.py`:
  - `stream(messages, model, **kwargs)` — async generator yielding string tokens
  - `complete(messages, model, **kwargs)` — returns full string + token counts
  - `list_available_models(config)` — returns models the user has keys for
- Handle provider errors gracefully (auth failures, rate limits, timeouts)
- **Done when:** streaming works against at least one live provider in a standalone test script

#### TASK-004 — Textual app skeleton
- Implement `tui/app.py` with:
  - Screen routing logic
  - Config check on startup: no config → SetupScreen, else → HomeScreen
  - Global keybindings: `q` quit, `s` settings, `h` history
- Implement `tui/screens/home.py` — static placeholder layout
- Implement `tui/styles/main.tcss` — base theme (background, font, colors)
- **Done when:** app launches, shows home screen, `q` exits cleanly

---

### Phase 2 — Setup & Settings

#### TASK-005 — Setup wizard screen
- Implement `tui/screens/setup.py`:
  - Input fields for all 4 providers (all optional)
  - Inline validation (non-empty fields get a ✓ indicator)
  - Model selector populated from entered keys
  - Save & Continue button writes config and routes to HomeScreen
- **Done when:** first-run flow saves config and launches home screen correctly

#### TASK-006 — Settings screen
- Implement `tui/screens/settings.py`:
  - Same form as setup wizard, pre-filled with masked current values
  - Saving updates config file and re-applies keys to `os.environ`
  - Cancel button discards changes
- **Done when:** keys can be updated mid-session without restart

---

### Phase 3 — Tools

#### TASK-007 — Search tool
- Implement `core/tools/search.py`:
  - `search(query, n)` — tries Tavily if key exists, falls back to DDG
  - Returns list of `SearchResult(title, url, snippet)`
- **Done when:** unit test retrieves results from both backends

#### TASK-008 — Scraper tool
- Implement `core/tools/scraper.py`:
  - `fetch_page(url)` — async httpx GET + readability extraction
  - Returns `PageContent(title, url, text, word_count)`
  - Timeout: 10s. Graceful error on non-HTML, paywalled, or 4xx/5xx pages
- **Done when:** scraper returns clean article text from 3 different test URLs

#### TASK-009 — Citation tracker
- Implement `core/tools/citations.py`:
  - `CitationTracker` class with `add(url, title, snippet) -> int` (returns index)
  - `get_all() -> list[Citation]`
  - `format_references() -> str` — numbered Markdown reference list
- **Done when:** citations accumulate correctly and render as `[1] Title — url`

---

### Phase 4 — LangGraph Pipeline

#### TASK-010 — Graph state + scaffold
- Implement `core/graph/state.py`:
  - Define `HiveState` TypedDict with all fields: `query`, `plan`, `browser_results`, `research_notes`, `synthesis`, `critique`, `citations`, `token_usage`, `iteration`, `messages`
  - Define `BrowserResult`, `CritiqueResult`, `Citation`, `TokenUsage` dataclasses
- Implement `core/graph/graph.py`:
  - Wire the `StateGraph` with all nodes and edges (stubs OK at this stage)
  - Compile with `SqliteSaver` checkpointer from `db/sessions.py`
- **Done when:** graph compiles and runs through stub nodes without error

#### TASK-011 — Planner node
- Implement `core/nodes/planner.py`:
  - Calls LLM with the user query
  - Returns a list of 2–4 focused sub-queries written into `state["plan"]`
  - Resets `iteration` counter to 0 on first run; increments on replan
- **Done when:** planner returns a sensible plan list for 3 different test queries

#### TASK-012 — Browser node (parallel fan-out)
- Implement `core/nodes/browser.py`:
  - Receives a single `sub_query` via LangGraph `Send` API
  - Calls search tool then scraper on top N results
  - Returns `BrowserResult` appended into `state["browser_results"]`
- Implement `core/graph/graph.py` fan-out edge using `Send`:
  ```python
  def plan_to_browse(state): 
      return [Send("browse", {"sub_query": q}) for q in state["plan"]]
  graph.add_conditional_edges("plan", plan_to_browse)
  ```
- **Done when:** multiple browser nodes run in parallel and all results land in state

#### TASK-013 — Researcher node
- Implement `core/nodes/researcher.py`:
  - Reads all `browser_results` from state
  - Calls LLM to extract key facts, quotes, and data points
  - Calls citation tracker for every sourced claim
  - Writes cited markdown notes into `state["research_notes"]`
- **Done when:** research notes contain inline citation markers tied to real URLs

#### TASK-014 — Synthesizer node
- Implement `core/nodes/synthesizer.py`:
  - Reads `research_notes` from state
  - Calls LLM to write a coherent, well-structured final answer
  - Preserves citation markers inline
  - Writes result into `state["synthesis"]`
- **Done when:** synthesis reads as a clean, cited research answer

#### TASK-015 — Critic node + conditional loop
- Implement `core/nodes/critic.py`:
  - Reads `synthesis` from state
  - Calls LLM to review for unsupported claims, gaps, and confidence
  - Writes `CritiqueResult(issues, confidence, follow_ups)` into `state["critique"]`
- Implement `core/graph/router.py`:
  - `should_continue(state)` — returns `"plan"` if confidence is low AND
    `iteration < 2`, otherwise returns `END`
- Add conditional edge in `graph.py`:
  ```python
  graph.add_conditional_edges("critique", should_continue, 
                               {"plan": "plan", END: END})
  ```
- **Done when:** low-quality synthesis triggers a replan loop; high-quality exits to END

---

### Phase 5 — TUI Research Screen

#### TASK-016 — Agent panel widget
- Implement `tui/widgets/agent_panel.py`:
  - Tree view of graph nodes with status icons: `◌ waiting`, `↻ running`, `✓ done`, `✗ error`
  - Driven by LangGraph `astream_events` — listens for `on_chain_start` and `on_chain_end` events keyed by node name
  - Browser fan-out nodes shown as children: `browse[0]`, `browse[1]`, etc.
- **Done when:** agent statuses update live during a real query driven by real graph events

#### TASK-017 — Chat widget with streaming
- Implement `tui/widgets/chat.py`:
  - Renders message history with role labels
  - Appends streaming tokens in real time as they arrive
  - Renders Markdown (bold, code blocks, headers) via `rich`
  - Auto-scrolls to bottom
- **Done when:** a streaming LLM response renders token-by-token without flicker

#### TASK-018 — Citations widget
- Implement `tui/widgets/citations.py`:
  - Horizontal bar below chat showing `[1] [2] [3]` badges
  - Hover/focus shows title + URL tooltip
  - Clicking opens URL in browser via `webbrowser.open()`
- **Done when:** citations appear and are navigable after a real query

#### TASK-019 — Status bar widget
- Implement `tui/widgets/statusbar.py`:
  - Shows: current model name, session token count, estimated cost in USD
  - Updates after every agent completes
- **Done when:** token count and cost update correctly after a full pipeline run

#### TASK-020 — Research screen assembly
- Implement `tui/screens/research.py`:
  - Assembles all widgets into the full layout
  - Wires query input → `graph.astream_events()` → streaming output + agent panel updates
  - `Ctrl+C` cancels the in-flight graph run cleanly via task cancellation
- **Done when:** full end-to-end query works through the complete TUI with live node status updates

---

### Phase 6 — Persistence & History

#### TASK-021 — SQLite layer + LangGraph checkpointer
- Implement `db/sessions.py`:
  - `get_connection()` — returns a shared SQLite connection
  - `create_session()`, `save_message()`, `save_citation()`, `list_sessions()`, `load_session(id)`
  - Async write queue so DB writes never block the TUI
  - The same connection is passed to `SqliteSaver` when compiling the graph —
    LangGraph writes its own checkpoint tables alongside the app's tables
- **Done when:** a session round-trips (save → reload → all messages and citations intact) AND LangGraph can resume a mid-run graph from the checkpoint

#### TASK-022 — History screen
- Implement `tui/screens/history.py`:
  - Scrollable list of past sessions: date, query snippet, model, cost
  - Search/filter input
  - Enter on a session loads it into the research screen (read-only)
- **Done when:** past sessions are browsable and loadable

---

### Phase 7 — Export

#### TASK-023 — Markdown export
- Implement `export/markdown.py`:
  - Renders session to Markdown with metadata header, cited body, references footer
  - Saves to `export.output_dir` with timestamped filename
- **Done when:** exported file opens correctly in any Markdown viewer

#### TASK-024 — PDF export
- Implement `export/pdf.py`:
  - Converts Markdown export to PDF via `weasyprint`
  - Applies minimal stylesheet
- **Done when:** PDF renders cleanly with working hyperlinks on citations

#### TASK-025 — Export keybind + confirmation
- Wire `e` keybind in research screen to trigger export flow
- Show a modal asking Markdown / PDF / Both
- Show confirmation with output file path after export
- **Done when:** export is fully operable from the keyboard with no mouse

---

### Phase 8 — Polish & Distribution

#### TASK-026 — Error handling pass
- Audit all agent and tool code for unhandled exceptions
- Add user-facing error messages in the TUI (not raw tracebacks)
- Handle: no API key for selected provider, search rate limit, scrape timeout, LLM context overflow
- **Done when:** all known error paths show a clean message and allow the user to continue

#### TASK-027 — Ollama integration test
- Verify the full pipeline works end-to-end with a local Ollama model
- Document required Ollama setup in README
- **Done when:** a full research query completes using only local models

#### TASK-028 — README
- Installation instructions (`uv tool install`, `pipx install`, Homebrew)
- Animated demo GIF (record with `vhs` or `asciinema`)
- Quick start guide
- API key setup instructions
- Keyboard shortcut reference

#### TASK-029 — PyPI publish
- Finalize `pyproject.toml` metadata (description, license, classifiers, homepage)
- `uv build` + `uv publish`
- Verify install from PyPI on a clean machine
- **Done when:** `uv tool install hive` works from PyPI and the app launches

#### TASK-030 — Homebrew tap
- Create `homebrew-tap` GitHub repo
- Write Formula file pointing to PyPI sdist
- Test `brew install yourusername/tap/research-assistant`

---

## Changelog Instructions

The file `CHANGELOG.md` must be maintained throughout development.
It lives at the root of the repository, alongside `README.md`.

### Format

Use [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format
with [Semantic Versioning](https://semver.org/):

```
## [Unreleased]

## [0.2.0] — YYYY-MM-DD
### Added
- ...

### Changed
- ...

### Fixed
- ...

### Removed
- ...
```

### Rules for the Agent Maintaining This File

1. **Every completed task gets a changelog entry.** When a task from
   this document is marked done, add an entry under `[Unreleased]`
   in the appropriate section (`Added`, `Changed`, `Fixed`, `Removed`).

2. **Entry format:** One line per task. Start with the task ID in
   brackets, then a plain-English description of what changed.
   Example: `[TASK-007] Added web search tool with Tavily and DDG fallback`

3. **On every new version release:** Move all entries from
   `[Unreleased]` into a new versioned section with today's date.
   Update version in `pyproject.toml` to match.

4. **Version bumping rules:**
   - New feature task completed → bump minor version (`0.1.0` → `0.2.0`)
   - Bug fix or polish task → bump patch version (`0.2.0` → `0.2.1`)
   - Breaking change to config schema or agent interface → bump major version

5. **Never delete old entries.** The changelog is a permanent record.

6. **Keep entries user-facing.** Write what the user gains or what
   broke, not internal implementation details.
   - Bad: `Refactored BaseAgent to use dataclasses instead of dicts`
   - Good: `[TASK-010] Agent pipeline now has a stable context interface`

7. **Breaking changes must be called out explicitly** with a
   `⚠ BREAKING:` prefix in the entry.

### Initial `CHANGELOG.md` Template

```markdown
# Changelog

All notable changes to hive are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [SemVer](https://semver.org/)

## [Unreleased]

## [0.1.0] — YYYY-MM-DD
### Added
- Initial project scaffold
```

---

*End of design document.*