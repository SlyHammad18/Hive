from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Select, Static

from hive.core.config import load_config, save_config, apply_config, mask_key
from hive.core.llm import fetch_provider_models, list_available_models
from hive.core.log import get_logger

_log = get_logger("settings")


def _provider_from_model(model: str) -> str:
    if "/" in model:
        return model.split("/", 1)[0]
    if model.startswith("gpt"):
        return "openai"
    if model.startswith("claude"):
        return "anthropic"
    return ""


class SettingsScreen(Screen[None]):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
    ]
    
    models_available: reactive[list[tuple[str, str]]] = reactive([])

    def compose(self) -> ComposeResult:
        cfg = load_config()
        providers = cfg.get("providers", {})
        defaults = cfg.get("defaults", {})
        search = cfg.get("search", {})

        with VerticalScroll(id="settings-scroll"):
            with Container(id="settings-header"):
                yield Static("⬡ HIVE", classes="page-logo")
                yield Static("Settings", classes="page-title")
                yield Static("Configure API keys, models, and search providers", classes="page-subtitle")

            with Container(classes="form-card"):
                yield Label("Provider API Keys", classes="section-header")

                self.inputs: dict[str, Input] = {}
                self.valid_icons: dict[str, Static] = {}
                fields = [
                    ("openai_api_key", "OpenAI"),
                    ("anthropic_api_key", "Anthropic"),
                    ("google_api_key", "Google"),
                    ("groq_api_key", "Groq"),
                    ("ollama_base_url", "Ollama Base URL"),
                ]
                for key, label_name in fields:
                    yield Label(label_name, classes="field-label-standalone")
                    with Horizontal(classes="field-input-row"):
                        current = providers.get(key, "")
                        placeholder = mask_key(current) if current else "Enter API key or URL"
                        inp = Input(
                            value=current,
                            placeholder=placeholder,
                            id=f"inp-{key}",
                            password=("key" in key),
                            classes="field-input-wide"
                        )
                        self.inputs[key] = inp
                        yield inp
                        icon = Static("✓" if current else "", classes="valid-icon-inline")
                        self.valid_icons[key] = icon
                        yield icon

            with Container(classes="form-card"):
                yield Label("Default Model", classes="section-header")
                self.model_select = Select[tuple[str, str]](
                    [], id="model-select", prompt="Select a model..."
                )
                yield self.model_select

            with Container(classes="form-card"):
                yield Label("Search", classes="section-header")
                yield Label("Tavily API Key", classes="field-label-standalone")
                with Horizontal(classes="field-input-row"):
                    tavily_current = search.get("tavily_api_key", "")
                    self.tavily_input = Input(
                        value=tavily_current,
                        placeholder=mask_key(tavily_current) if tavily_current else "Optional",
                        id="inp-tavily_api_key",
                        password=True,
                        classes="field-input-wide"
                    )
                    yield self.tavily_input
                    self.tavily_icon = Static("✓" if tavily_current else "", classes="valid-icon-inline")
                    yield self.tavily_icon

            with Container(id="settings-button-container"):
                with Horizontal(id="settings-buttons"):
                    yield Button("Cancel", id="cancel-btn", variant="default")
                    yield Button("Save", id="save-btn", variant="primary")
        
        yield Static("[#f59e0b]Esc[/] Home  │  [#f59e0b]Enter[/] Save", id="settings-hints")

    def on_mount(self) -> None:
        self._rebuild_models()
        cfg = load_config()
        defaults = cfg.get("defaults", {})
        model = defaults.get("model", "")
        if model:
            self.model_select.value = model
        for key, inp in self.inputs.items():
            val = inp.value.strip()
            if val:
                self.set_timer(0.1, lambda k=key, v=val: self._fetch_fresh_models(k, v))

    def on_input_changed(self, event: Input.Changed) -> None:
        input_id = event.input.id or ""
        if input_id.startswith("inp-"):
            key = input_id.removeprefix("inp-")
            if key in self.valid_icons:
                icon = self.valid_icons[key]
                icon.update("✓" if event.value.strip() else "")
        if input_id == "inp-tavily_api_key":
            self.tavily_icon.update("✓" if event.value.strip() else "")
        self._rebuild_models()

    def _rebuild_models(self) -> None:
        providers = {}
        for key, inp in self.inputs.items():
            val = inp.value.strip()
            if val:
                providers[key] = val
        _log.debug("_rebuild_models: providers=%s", set(providers.keys()))
        config = {"providers": providers}
        models = list_available_models(config)
        saved_cfg = load_config()
        saved_model = saved_cfg.get("defaults", {}).get("model", "")
        if saved_model and saved_model not in models:
            _log.debug("  prepending saved model %s", saved_model)
            models.insert(0, saved_model)
        _log.debug("  final models (%d): %s", models)
        options = [(m, m) for m in models]
        self.models_available = options

    def watch_models_available(self, options: list[tuple[str, str]]) -> None:
        self.model_select.set_options(options)
        self.model_select.disabled = len(options) == 0

    async def _fetch_fresh_models(self, provider_key: str, value: str) -> None:
        await fetch_provider_models(provider_key, value)
        self._rebuild_models()

    def action_home(self) -> None:
        """Navigate back to home screen."""
        # Pop all screens to get back to home
        while len(self.app.screen_stack) > 1:
            self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            self._save()
        elif event.button.id == "cancel-btn":
            self.action_home()

    def _save(self) -> None:
        providers = {}
        for key, inp in self.inputs.items():
            val = inp.value.strip()
            if val:
                providers[key] = val
            else:
                providers[key] = ""
        config_data: dict = {"providers": providers}

        tavily = self.tavily_input.value.strip()
        config_data["search"] = {"tavily_api_key": tavily}

        model: object = self.model_select.value
        if model and isinstance(model, str):
            config_data["defaults"] = {
                "model": model,
                "provider": _provider_from_model(model),
            }

        save_config(config_data)
        apply_config(config_data)

        self.action_home()
