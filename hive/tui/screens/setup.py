from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Label


class SetupScreen(Screen[None]):
    def compose(self) -> ComposeResult:
        yield Label("Welcome to hive!\n\nNo configuration found.\nSetup wizard coming soon.")
