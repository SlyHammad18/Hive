from hive.core.config import apply_config, load_config
from hive.core.llm import clear_model_cache
from hive.core.log import get_logger
from hive.tui.app import HiveApp

_log = get_logger("main")


def main() -> None:
    _log.info("=== hive starting ===")
    clear_model_cache()
    cfg = load_config()
    _log.info("config loaded, providers: %s", set(cfg.get("providers", {}).keys()))
    apply_config(cfg)
    app = HiveApp()
    app.run()
    _log.info("=== hive exiting ===")
