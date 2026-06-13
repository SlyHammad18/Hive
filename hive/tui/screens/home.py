from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Input, Label

from hive.tui.screens.research import ResearchScreen


class HomeScreen(Screen[None]):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(
            "hive — research assistant\n\nEnter a query below to start researching.\n\n"
            "Press s for settings, h for history, q to quit.",
            id="home-label",
        )
        yield Input(id="home-query", placeholder="Enter a research query...")
        yield Footer()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if query:
            self.app.push_screen(ResearchScreen(initial_query=query))
