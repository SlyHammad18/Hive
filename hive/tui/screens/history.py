from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Container, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Input, Label, ListItem, ListView, Static

from hive.db.sessions import list_sessions


class HistoryScreen(Screen[None]):
    BINDINGS = [
        Binding("escape", "back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="history-scroll"):
            with Container(id="history-header"):
                yield Static("⬡ HIVE", classes="page-logo")
                yield Static("Research History", classes="page-title")
                yield Static("View and continue past research sessions", classes="page-subtitle")
            yield Input(id="history-search", placeholder="Search past sessions...", classes="search-input")
            yield ListView(id="session-list")
        yield Static("[#f59e0b]Esc[/] Back\n[#f59e0b]Enter[/] Open Session", id="history-hints")

    async def on_mount(self) -> None:
        await self._refresh()

    async def on_input_changed(self, event: Input.Changed) -> None:
        await self._refresh(event.value.strip())

    async def _refresh(self, search: str = "") -> None:
        sessions = await list_sessions()
        list_view = self.query_one("#session-list", ListView)
        list_view.clear()
        if not sessions:
            empty_label = Label("No research sessions yet\nStart a new query from the home screen", classes="empty-state")
            list_view.append(ListItem(empty_label))
            return
        for s in sessions:
            if search and search.lower() not in s.query.lower():
                continue
            date_str = s.created_at.strftime("%Y-%m-%d %H:%M")
            snippet = s.query[:60]
            cost_str = f"${s.cost_usd:.4f}" if s.cost_usd else ""
            
            label_text = f"[bold #e2e8f0]{snippet}[/]\n[#64748b]{date_str}[/]\n[#64748b]Model: {s.model}[/]" + (f"\n[#64748b]Cost: {cost_str}[/]" if cost_str else "")
            
            list_view.append(
                ListItem(
                    Label(label_text),
                    id=f"session-{s.id}",
                )
            )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item and event.item.id and event.item.id.startswith("session-"):
            session_id = event.item.id.removeprefix("session-")
            self._load_session(session_id)

    def _load_session(self, session_id: str) -> None:
        from hive.tui.screens.research import ResearchScreen

        self.app.push_screen(ResearchScreen(session_id=session_id))

    def action_back(self) -> None:
        self.app.pop_screen()
