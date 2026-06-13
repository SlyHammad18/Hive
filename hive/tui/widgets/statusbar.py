from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static


class StatusBar(Horizontal):
    def __init__(self) -> None:
        super().__init__(id="status-bar")
        self._model = Static("", id="status-model", classes="status-item")
        self._tokens = Static("", id="status-tokens", classes="status-item")
        self._cost = Static("", id="status-cost", classes="status-item")

    def compose(self) -> ComposeResult:
        yield self._model
        yield self._tokens
        yield self._cost

    def set_model(self, model: str) -> None:
        self._model.update(model)

    def set_token_usage(self, prompt: int, completion: int, total: int) -> None:
        self._tokens.update(f"{total:,} tok  ({prompt:,}↑ {completion:,}↓)")

    def set_cost(self, cost_usd: float) -> None:
        self._cost.update(f"${cost_usd:.4f}")

    def reset_counts(self) -> None:
        self._tokens.update("0 tok")
        self._cost.update("$0.0000")

    def update_from_graph(
        self, model: str, prompt_tokens: int, completion_tokens: int, total_tokens: int, cost_usd: float
    ) -> None:
        self._model.update(model)
        self._tokens.update(f"{total_tokens:,} tok  ({prompt_tokens:,}↑ {completion_tokens:,}↓)")
        self._cost.update(f"${cost_usd:.4f}")
