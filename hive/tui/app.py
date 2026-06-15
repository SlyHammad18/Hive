import asyncio

from textual.app import App
from textual.binding import Binding

from hive.core.config import load_config
from hive.core.log import get_logger
from hive.db.sessions import shutdown as _shutdown_db
from hive.tui.screens.home import HomeScreen
from hive.tui.screens.setup import SetupScreen
from hive.tui.screens.settings import SettingsScreen
from hive.tui.screens.history import HistoryScreen

_log = get_logger("tui.app")


class HiveApp(App[None]):
    CSS_PATH = "styles/main.tcss"
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("f1", "push_screen('settings')", "Settings"),
        Binding("f2", "push_screen('history')", "History"),
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

    async def action_quit(self) -> None:
        _log.info("Ctrl+Q pressed — initiating shutdown")
        # Cancel any active research tasks before shutting down the DB
        await self._cancel_all_research_tasks()
        await _shutdown_db()
        _log.info("App exiting")
        self.exit()

    async def _cancel_all_research_tasks(self) -> None:
        screens_to_check = list(self.screen_stack) + [self.screen]
        for screen in screens_to_check:
            task = getattr(screen, "_research_task", None)
            if task is not None and not task.done():
                _log.info("Cancelling research task on %s", type(screen).__name__)
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    _log.info("Research task cancelled cleanly")
                except Exception as exc:
                    _log.warning("Error awaiting cancelled research task: %s", exc)
