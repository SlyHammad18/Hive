from textual.app import App
from textual.binding import Binding

from hive.core.config import load_config
from hive.tui.screens.home import HomeScreen
from hive.tui.screens.setup import SetupScreen
from hive.tui.screens.settings import SettingsScreen
from hive.tui.screens.history import HistoryScreen


class HiveApp(App[None]):
    CSS_PATH = "styles/main.tcss"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("s", "push_screen('settings')", "Settings", priority=True),
        Binding("h", "push_screen('history')", "History", priority=True),
    ]

    SCREENS = {
        "setup": SetupScreen,
        "home": HomeScreen,
        "settings": SettingsScreen,
        "history": HistoryScreen,
    }

    def on_mount(self) -> None:
        config = load_config()
        if config:
            self.push_screen("home")
        else:
            self.push_screen("setup")
