from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Label


class HistoryScreen(Screen[None]):
    def compose(self) -> ComposeResult:
        yield Label("History — coming soon")
