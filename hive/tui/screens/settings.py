from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Select, Static

from hive.core.config import load_config, save_config, apply_config, mask_key
from hive.core.llm import fetch_provider_models, list_available_models


def _provider_from_model(model: str) -> str:
    if "/" in model:
        return model.split("/", 1)[0]
    if model.startswith("gpt"):
        return "openai"
    if model.startswith("claude"):
        return "anthropic"
    return ""


class SettingsScreen(Screen[None]):
    models_available: reactive[list[tuple[str, str]]] = reactive([])

    def compose(self) -> ComposeResult:
        cfg = load_config()
        providers = cfg.get("providers", {})
        defaults = cfg.get("defaults", {})
        search = cfg.get("search", {})

        with VerticalScroll(id="setup-scroll"):
            yield Label("Settings", id="setup-title")

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
                with Horizontal(classes="field-row"):
                    yield Label(label_name, classes="field-label")
                    current = providers.get(key, "")
                    placeholder = mask_key(current) if current else "Enter API key or URL"
                    inp = Input(
                        value=current,
                        placeholder=placeholder,
                        id=f"inp-{key}",
                        password=("key" in key),
                    )
                    self.inputs[key] = inp
                    yield inp
                    icon = Static("✓" if current else "", classes="valid-icon")
                    icon.styles.color = "#4ade80" if current else "transparent"
                    self.valid_icons[key] = icon
                    yield icon

            yield Label("Default Model", classes="section-header")
            self.model_select = Select[tuple[str, str]](
                [], id="model-select", prompt="Select a model..."
            )
            yield self.model_select

            yield Label("Search", classes="section-header")
            with Horizontal(classes="field-row"):
                yield Label("Tavily API Key", classes="field-label")
                tavily_current = search.get("tavily_api_key", "")
                self.tavily_input = Input(
                    value=tavily_current,
                    placeholder=mask_key(tavily_current) if tavily_current else "Optional",
                    id="inp-tavily_api_key",
                    password=True,
                )
                yield self.tavily_input
                self.tavily_icon = Static("✓" if tavily_current else "", classes="valid-icon")
                self.tavily_icon.styles.color = "#4ade80" if tavily_current else "transparent"
                yield self.tavily_icon

            with Horizontal(id="settings-buttons"):
                yield Button("Cancel", id="cancel-btn", variant="default")
                yield Button("Save", id="save-btn", variant="primary")

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
                icon.styles.color = "#4ade80" if event.value.strip() else "transparent"
        if input_id == "inp-tavily_api_key":
            self.tavily_icon.update("✓" if event.value.strip() else "")
            self.tavily_icon.styles.color = "#4ade80" if event.value.strip() else "transparent"
        self._rebuild_models()

    def _rebuild_models(self) -> None:
        providers = {}
        for key, inp in self.inputs.items():
            val = inp.value.strip()
            if val:
                providers[key] = val
        config = {"providers": providers}
        models = list_available_models(config)
        saved_cfg = load_config()
        saved_model = saved_cfg.get("defaults", {}).get("model", "")
        if saved_model and saved_model not in models:
            models.insert(0, saved_model)
        options = [(m, m) for m in models]
        self.models_available = options

    def watch_models_available(self, options: list[tuple[str, str]]) -> None:
        self.model_select.set_options(options)
        self.model_select.disabled = len(options) == 0

    async def _fetch_fresh_models(self, provider_key: str, value: str) -> None:
        await fetch_provider_models(provider_key, value)
        self._rebuild_models()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            self._save()
        elif event.button.id == "cancel-btn":
            self.app.pop_screen()

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

        self.app.pop_screen()
