from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Header, Footer, Input, Label, ListItem, ListView

from hive.db.sessions import list_sessions


class HistoryScreen(Screen[None]):
    BINDINGS = [
        Binding("escape", "back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Input(id="history-search", placeholder="Search past sessions...")
        with VerticalScroll():
            yield ListView(id="session-list")
        yield Footer()

    async def on_mount(self) -> None:
        await self._refresh()

    async def on_input_changed(self, event: Input.Changed) -> None:
        await self._refresh(event.value.strip())

    async def _refresh(self, search: str = "") -> None:
        sessions = await list_sessions()
        list_view = self.query_one("#session-list", ListView)
        list_view.clear()
        if not sessions:
            list_view.append(ListItem(Label("No past sessions yet.")))
            return
        for s in sessions:
            if search and search.lower() not in s.query.lower():
                continue
            date_str = s.created_at.strftime("%Y-%m-%d %H:%M")
            snippet = s.query[:60]
            cost_str = f"${s.cost_usd:.4f}" if s.cost_usd else ""
            list_view.append(
                ListItem(
                    Label(f"{date_str} | {snippet} | {s.model} | {cost_str}"),
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
