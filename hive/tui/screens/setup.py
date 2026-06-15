from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Select, Static

from hive.core.config import save_config, apply_config
from hive.core.llm import fetch_provider_models, list_available_models


def _provider_from_model(model: str) -> str:
    if "/" in model:
        return model.split("/", 1)[0]
    if model.startswith("gpt"):
        return "openai"
    if model.startswith("claude"):
        return "anthropic"
    return ""


class SetupScreen(Screen[None]):
    models_available: reactive[list[tuple[str, str]]] = reactive([])

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="setup-scroll"):
            with Container(id="setup-header"):
                yield Static("⬡ HIVE", classes="page-logo")
                yield Static("Welcome to Hive", classes="page-title")
                yield Static("API keys are stored locally and never shared.", classes="page-subtitle")

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
                        inp = Input(placeholder="Enter API key or URL", id=f"inp-{key}", password=("key" in key), classes="field-input-wide")
                        self.inputs[key] = inp
                        yield inp
                        icon = Static("", classes="valid-icon-inline")
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
                    self.tavily_input = Input(placeholder="Optional — DuckDuckGo used otherwise", id="inp-tavily_api_key", password=True, classes="field-input-wide")
                    yield self.tavily_input
                    self.tavily_icon = Static("", classes="valid-icon-inline")
                    yield self.tavily_icon

            yield Button("Save & Continue →", id="save-btn", variant="primary")
        
        yield Static("[#f59e0b]Tab[/] Navigate  │  [#f59e0b]Enter[/] Save & Continue", id="setup-hints")

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
        config = {"providers": providers}
        models = list_available_models(config)
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

    def _save(self) -> None:
        providers = {}
        for key, inp in self.inputs.items():
            val = inp.value.strip()
            if val:
                providers[key] = val
        config_data: dict = {"providers": providers}

        tavily = self.tavily_input.value.strip()
        if tavily:
            config_data["search"] = {"tavily_api_key": tavily}

        model: object = self.model_select.value
        if model and isinstance(model, str):
            config_data["defaults"] = {
                "model": model,
                "provider": _provider_from_model(model),
            }

        save_config(config_data)
        apply_config(config_data)

        self.app.switch_screen("home")
