from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Label


class HomeScreen(Screen[None]):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("hive — research assistant\n\nPress s for settings, h for history, q to quit.", id="home-label")
        yield Footer()
