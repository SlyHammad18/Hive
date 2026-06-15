from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static

class StatusBar(Horizontal):
    def __init__(self) -> None:
        super().__init__(id="status-bar")
        self._model = Static("", classes="status-model")
        self._sep1 = Static("│", classes="status-sep")
        self._tokens = Static("0 tok", classes="status-tokens")
        self._sep2 = Static("│", classes="status-sep")
        self._cost = Static("$ 0.0000", classes="status-cost")

    def compose(self) -> ComposeResult:
        yield self._model
        yield self._sep1
        yield self._tokens
        yield self._sep2
        yield self._cost

    def set_model(self, model: str) -> None:
        if model:
            self._model.update(f"⬡ {model}")
        else:
            self._model.update("")

    def set_token_usage(self, prompt: int, completion: int, total: int) -> None:
        self._tokens.update(f"⬆ {prompt:,}  ⬇ {completion:,}  Σ {total:,}")

    def set_cost(self, cost_usd: float) -> None:
        self._cost.update(f"$ {cost_usd:.4f}")

    def reset_counts(self) -> None:
        self._tokens.update("0 tok")
        self._cost.update("$ 0.0000")

    def update_from_graph(
        self, model: str, prompt_tokens: int, completion_tokens: int, total_tokens: int, cost_usd: float
    ) -> None:
        self.set_model(model)
        self.set_token_usage(prompt_tokens, completion_tokens, total_tokens)
        self.set_cost(cost_usd)
