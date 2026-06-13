from __future__ import annotations

import asyncio
import uuid

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Header, Input

from hive.core.config import load_config
from hive.core.graph.graph import compile_graph_async
from hive.core.graph.state import TokenUsage
from hive.tui.widgets.agent_panel import AgentPanel
from hive.tui.widgets.chat import ChatWidget
from hive.tui.widgets.citations import CitationsWidget
from hive.tui.widgets.statusbar import StatusBar


_ESTIMATED_COST_PER_TOKEN = 0.00001


class ResearchScreen(Screen[None]):
    BINDINGS = [
        Binding("ctrl+c", "cancel", "Cancel"),
        Binding("e", "export", "Export"),
        Binding("n", "new_session", "New"),
    ]

    def __init__(self, initial_query: str = "") -> None:
        super().__init__()
        self._initial_query = initial_query
        self._research_task: asyncio.Task[None] | None = None
        self._agent_statuses: dict[str, str] = {}
        self.agent_panel = AgentPanel()
        self.chat = ChatWidget()
        self.citations_widget = CitationsWidget()
        self.status_bar = StatusBar()
        self.query_input = Input(id="query-input", placeholder="Enter a research query...")

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="research-header"):
            yield self.status_bar
        with Horizontal(id="research-body"):
            with VerticalScroll(id="left-panel", classes="panel"):
                yield self.agent_panel
                yield self.citations_widget
            with Vertical(id="right-panel", classes="panel"):
                yield self.chat
        with Horizontal(id="input-bar"):
            yield self.query_input

    def on_mount(self) -> None:
        cfg = load_config()
        defaults = cfg.get("defaults", {})
        model = defaults.get("model", "")
        if model:
            self.status_bar.set_model(model)
        if self._initial_query:
            self.query_input.value = self._initial_query
            self._start_research(self._initial_query)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if query:
            self._start_research(query)

    def _start_research(self, query: str) -> None:
        self.query_input.clear()
        self.query_input.disabled = True
        self.agent_panel.reset()
        self.chat.clear()
        self.citations_widget.clear()
        self.status_bar.reset_counts()
        self.chat.add_message("user", query)
        self._research_task = asyncio.create_task(self._run_research(query))

    async def _run_research(self, query: str) -> None:
        try:
            app = await compile_graph_async()
            config = {"configurable": {"thread_id": str(uuid.uuid4())}}
            model = load_config().get("defaults", {}).get("model", "unknown")

            total_tokens = TokenUsage()

            async for event in app.astream_events(
                {"query": query}, config, version="v2"
            ):
                kind = event["event"]
                name = event.get("name", "")
                node_names = {"plan", "browse", "research", "synthesize", "critique"}

                if kind == "on_chain_start" and name in node_names:
                    self.agent_panel.agent_statuses = {**self._agent_statuses, name: "running"}
                    self._agent_statuses[name] = "running"
                elif kind == "on_chain_end" and name in node_names:
                    self.agent_panel.agent_statuses = {**self._agent_statuses, name: "done"}
                    self._agent_statuses[name] = "done"

            final_state = app.get_state(config)
            state_values = final_state.values

            synthesis = state_values.get("synthesis", "")
            if synthesis:
                self.chat.add_message("assistant", synthesis)

            citations = state_values.get("citations", [])
            if citations:
                self.citations_widget.set_citations(citations)

            tu = state_values.get("token_usage")
            if tu:
                self.status_bar.set_token_usage(tu.prompt_tokens, tu.completion_tokens, tu.total_tokens)
                cost = (tu.prompt_tokens + tu.completion_tokens) * _ESTIMATED_COST_PER_TOKEN
                self.status_bar.set_cost(cost)

        except asyncio.CancelledError:
            self.chat.add_message("assistant", "Research cancelled.")
        except Exception as exc:
            self.chat.add_message("assistant", f"Research failed: {exc}")
        finally:
            self.query_input.disabled = False
            self.query_input.focus()

    def action_cancel(self) -> None:
        if self._research_task and not self._research_task.done():
            self._research_task.cancel()

    def action_export(self) -> None:
        pass

    def action_new_session(self) -> None:
        self._agent_statuses = {}
        self.agent_panel.reset()
        self.chat.clear()
        self.citations_widget.clear()
        self.query_input.clear()
        self.query_input.disabled = False
        self.query_input.focus()
