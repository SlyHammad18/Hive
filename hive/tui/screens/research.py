from __future__ import annotations

import asyncio
import uuid

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Input, Select, Static

import aiosqlite

from hive.core.config import load_config, save_config
from hive.core.graph.graph import compile_graph_async
from hive.core.llm import list_available_models
from hive.core.log import get_logger
from hive.db.sessions import SessionInfo, create_session, get_async_connection, load_session, save_citation, save_message
from hive.tui.widgets.agent_panel import AgentPanel
from hive.tui.widgets.chat import ChatWidget
from hive.tui.widgets.citations import CitationsWidget
from hive.tui.widgets.statusbar import StatusBar

_log = get_logger("tui.research")

_ESTIMATED_COST_PER_TOKEN = 0.00001


class ResearchScreen(Screen[None]):
    BINDINGS = [
        Binding("ctrl+c", "cancel", "Cancel"),
        Binding("escape", "back", "Back"),
        Binding("e", "export", "Export"),
        Binding("n", "new_session", "New"),
    ]

    def __init__(self, initial_query: str = "", session_id: str | None = None) -> None:
        super().__init__()
        self._initial_query = initial_query
        self._session_id = session_id
        self._research_task: asyncio.Task[None] | None = None
        self._agent_statuses: dict[str, str] = {}
        self._agent_outputs: dict[str, str] = {}
        self.agent_panel = AgentPanel()
        self.chat = ChatWidget()
        self.citations_widget = CitationsWidget()
        self.status_bar = StatusBar()
        self.query_input = Input(id="query-input", placeholder="Enter a research query...")
        
        # Model selector
        cfg = load_config()
        models = list_available_models(cfg)
        saved_model = cfg.get("defaults", {}).get("model", "")
        if saved_model and saved_model not in models:
            models.insert(0, saved_model)
        model_options = [(m, m) for m in models]
        current_model = saved_model or (models[0] if models else "")
        self.model_select = Select(model_options, id="model-select-input", value=current_model, allow_blank=False)

    def compose(self) -> ComposeResult:
        with Horizontal(id="research-title-bar"):
            yield Static("⬡ HIVE", classes="title-brand")
            yield self.status_bar
        with Horizontal(id="research-body"):
            with VerticalScroll(id="left-panel", classes="panel"):
                yield self.agent_panel
                yield self.citations_widget
            with Vertical(id="right-panel", classes="panel"):
                with ScrollableContainer(id="chat-container"):
                    yield self.chat
        with Horizontal(id="input-bar"):
            yield Static("Model:", id="model-label")
            yield self.model_select
            yield self.query_input
        yield Static("[#64748b]Esc[/] Back  │  [#64748b]N[/] New  │  [#64748b]E[/] Export  │  [#64748b]Ctrl+C[/] Cancel", id="action-hints")

    async def on_mount(self) -> None:
        if self._session_id:
            session = await load_session(self._session_id)
            if session:
                self._display_session(session)
            else:
                self.chat.add_message("assistant", "Session not found.")
            return
        cfg = load_config()
        defaults = cfg.get("defaults", {})
        model = defaults.get("model", "")
        if model:
            self.status_bar.set_model(model)
        if self._initial_query:
            self.query_input.value = self._initial_query
            self._start_research(self._initial_query)

    def _display_session(self, session: SessionInfo) -> None:
        self.query_input.disabled = True
        self.query_input.placeholder = "Read-only: viewing past session"
        self.status_bar.set_model(session.model)
        tu = session.token_usage
        self.status_bar.set_token_usage(
            tu.get("prompt_tokens", 0),
            tu.get("completion_tokens", 0),
            tu.get("total_tokens", 0),
        )
        total = tu.get("prompt_tokens", 0) + tu.get("completion_tokens", 0)
        self.status_bar.set_cost(total * _ESTIMATED_COST_PER_TOKEN)
        for msg in session.messages:
            self.chat.add_message(msg.role, msg.content)
        if session.citations:
            self.citations_widget.set_citations(session.citations)

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle model selection changes."""
        if event.select.id == "model-select-input" and event.value:
            model = str(event.value)
            cfg = load_config()
            cfg["defaults"] = cfg.get("defaults", {})
            cfg["defaults"]["model"] = model
            # Determine provider from model name
            if "/" in model:
                cfg["defaults"]["provider"] = model.split("/", 1)[0]
            elif model.startswith("gpt"):
                cfg["defaults"]["provider"] = "openai"
            elif model.startswith("claude"):
                cfg["defaults"]["provider"] = "anthropic"
            save_config(cfg)
            self.status_bar.set_model(model)
            _log.info(f"Model changed to: {model}")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if query:
            self._start_research(query)

    def _start_research(self, query: str) -> None:
        _log.info("Starting research: query='%s'", query[:80])
        self.query_input.clear()
        self.query_input.disabled = True
        self.model_select.disabled = True
        self.agent_panel.reset()
        self.chat.clear()
        self.citations_widget.clear()
        self.status_bar.reset_counts()
        self._agent_outputs = {}
        self.chat.add_message("user", query)
        self._research_task = asyncio.create_task(self._run_research(query))

    async def _run_research(self, query: str) -> None:
        session_id = str(uuid.uuid4())
        conn: aiosqlite.Connection | None = None
        try:
            conn = await get_async_connection()
            app = await compile_graph_async(connection=conn)
            config = {"configurable": {"thread_id": session_id}}
            cfg = load_config()
            defaults = cfg.get("defaults", {})
            model = defaults.get("model", "unknown")
            provider = defaults.get("provider", "")

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
                    
                    # Extract output data for each step
                    data = event.get("data", {})
                    output = data.get("output", {})
                    
                    if name == "plan":
                        plan_text = output.get("plan", "")
                        if plan_text:
                            self._agent_outputs["plan"] = plan_text
                            self.chat.add_message("system", f"[bold #f59e0b]Plan:[/]\n{plan_text}")
                    
                    elif name == "browse":
                        urls = output.get("urls", [])
                        if urls:
                            urls_text = "\n".join([f"  • {url}" for url in urls])
                            self._agent_outputs[f"browse_{len([k for k in self._agent_outputs if k.startswith('browse')])}"] = urls_text
                            self.chat.add_message("system", f"[bold #f59e0b]Browsing:[/]\n{urls_text}")
                    
                    elif name == "research":
                        findings = output.get("findings", "")
                        if findings:
                            self._agent_outputs["research"] = findings
                            self.chat.add_message("system", f"[bold #f59e0b]Research Findings:[/]\n{findings[:500]}...")
                    
                    elif name == "critique":
                        feedback = output.get("feedback", "")
                        if feedback:
                            self._agent_outputs["critique"] = feedback
                            self.chat.add_message("system", f"[bold #f59e0b]Critique:[/]\n{feedback}")

            final_state = await app.aget_state(config)
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

            token_dict = {}
            cost_val = 0.0
            if tu:
                token_dict = {
                    "prompt_tokens": tu.prompt_tokens,
                    "completion_tokens": tu.completion_tokens,
                    "total_tokens": tu.total_tokens,
                }
                cost_val = (tu.prompt_tokens + tu.completion_tokens) * _ESTIMATED_COST_PER_TOKEN

            try:
                await create_session(
                    session_id=session_id,
                    query=query,
                    provider=provider,
                    model=model,
                    token_usage=token_dict,
                    cost_usd=cost_val,
                )
                await save_message(session_id, "user", query)
                if synthesis:
                    await save_message(session_id, "assistant", synthesis, agent_name="Synthesizer")
                for c in citations:
                    await save_citation(session_id, c)
                _log.info("Session %s saved (db writes queued)", session_id)
            except Exception as exc:
                _log.error("Failed to save session %s: %s", session_id, exc, exc_info=True)

        except asyncio.CancelledError:
            _log.warning("Research cancelled for session %s", session_id)
            self.chat.add_message("assistant", "Research cancelled.")
        except Exception as exc:
            _log.error("Research failed for session %s: %s", session_id, exc, exc_info=True)
            self.chat.add_message("assistant", f"Research failed: {exc}")
        finally:
            if conn is not None:
                try:
                    await conn.close()
                    _log.debug("Async DB connection closed for session %s", session_id)
                except Exception as exc:
                    _log.warning("Error closing DB connection: %s", exc)
            self.query_input.disabled = False
            self.model_select.disabled = False
            self.query_input.focus()

    async def on_unmount(self) -> None:
        await self._cancel_task()

    async def _cancel_task(self) -> None:
        if self._research_task and not self._research_task.done():
            self._research_task.cancel()
            try:
                await self._research_task
            except asyncio.CancelledError:
                pass

    def action_cancel(self) -> None:
        if self._research_task and not self._research_task.done():
            self._research_task.cancel()

    def action_back(self) -> None:
        if self._research_task and not self._research_task.done():
            self._research_task.cancel()
        self.app.pop_screen()

    def action_export(self) -> None:
        pass

    def action_new_session(self) -> None:
        self._agent_statuses = {}
        self._agent_outputs = {}
        self.agent_panel.reset()
        self.chat.clear()
        self.citations_widget.clear()
        self.query_input.clear()
        self.query_input.disabled = False
        self.model_select.disabled = False
        self.query_input.focus()
