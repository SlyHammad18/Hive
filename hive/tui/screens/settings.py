from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Label


class SettingsScreen(Screen[None]):
    def compose(self) -> ComposeResult:
        yield Label("Settings — coming soon")
