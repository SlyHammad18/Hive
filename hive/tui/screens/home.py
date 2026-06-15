from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Input, Static

from hive.tui.screens.research import ResearchScreen

_LOGO = r"""
██╗  ██╗ ██╗ ██╗   ██╗ ███████╗
██║  ██║ ██║ ██║   ██║ ██╔════╝
███████║ ██║ ██║   ██║ █████╗  
██╔══██║ ██║ ╚██╗ ██╔╝ ██╔══╝  
██║  ██║ ██║  ╚████╔╝  ███████╗
╚═╝  ╚═╝ ╚═╝   ╚═══╝   ╚══════╝
"""


class HomeScreen(Screen[None]):
    def compose(self) -> ComposeResult:
        with Center(id="home-container"):
            with Vertical(id="home-inner"):
                yield Static(_LOGO, id="home-logo")
                yield Static(
                    "Multi-agent research assistant",
                    id="home-tagline",
                )
                yield Input(
                    id="home-query",
                    placeholder="What would you like to research?",
                )
                yield Static(
                    "[#f59e0b]F1[/] Settings  │  [#f59e0b]F2[/] History  │  [#f59e0b]Ctrl+Q[/] Quit",
                    id="home-hints",
                )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if query:
            self.app.push_screen(ResearchScreen(initial_query=query))
