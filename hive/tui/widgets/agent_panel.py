from textual.app import ComposeResult
from textual.reactive import reactive
from textual.containers import VerticalScroll
from textual.widgets import Static

_NODE_NAMES = ["plan", "browse", "research", "synthesize", "critique"]
_STATUS_ICONS = {
    "waiting": "◌",
    "running": "↻",
    "done": "✓",
    "error": "✗",
}


def _icon(status: str) -> str:
    return _STATUS_ICONS.get(status, "◌")


def _safe_id(name: str) -> str:
    return "agent-" + name.replace("[", "-").replace("]", "")


class AgentPanel(VerticalScroll):
    agent_statuses: reactive[dict[str, str]] = reactive({}, always_update=True)

    def __init__(self) -> None:
        super().__init__(id="agent-panel")
        self._lines: dict[str, Static] = {}
        self._browse_counter = 0

    def compose(self) -> ComposeResult:
        yield Static("Agents", classes="section-header")
        for name in _NODE_NAMES:
            line = Static(f"{_icon('waiting')} {name.capitalize()}", id=_safe_id(name))
            self._lines[name] = line
            yield line

    def watch_agent_statuses(self, statuses: dict[str, str]) -> None:
        for name, status in statuses.items():
            if name == "browse" and status == "running":
                self._browse_counter += 1
                label = f"browse[{self._browse_counter}]"
                line = Static(f"{_icon('running')} {label}", id=_safe_id(label))
                self._lines[label] = line
                self.mount(line, before=self._lines.get("research"))
            elif name in self._lines:
                self._lines[name].update(f"{_icon(status)} {name.capitalize() if name in _NODE_NAMES else name}")

    def reset(self) -> None:
        self._browse_counter = 0
        for key, line in list(self._lines.items()):
            if key.startswith("browse["):
                try:
                    line.remove()
                except Exception:
                    pass
                del self._lines[key]
            else:
                line.update(f"{_icon('waiting')} {key.capitalize()}")
