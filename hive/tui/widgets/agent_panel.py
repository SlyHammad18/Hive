import time

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.containers import VerticalScroll
from textual.widgets import Static

_NODE_NAMES = ["plan", "browse", "research", "synthesize", "critique"]
_SPINNERS = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

def _safe_id(name: str) -> str:
    return "agent-" + name.replace("[", "-").replace("]", "")

class AgentPanel(VerticalScroll):
    agent_statuses: reactive[dict[str, str]] = reactive({}, always_update=True)

    def __init__(self) -> None:
        super().__init__(id="agent-panel")
        self._lines: dict[str, Static] = {}
        self._browse_counter = 0
        self._spinner_idx = 0
        self._start_times: dict[str, float] = {}

    def compose(self) -> ComposeResult:
        yield Static("⬡ AGENTS", classes="agent-section-title")
        for name in _NODE_NAMES:
            line = Static(f"  ◌  {name.capitalize()}", id=_safe_id(name), classes="agent-row agent-icon-waiting")
            self._lines[name] = line
            yield line

    def on_mount(self) -> None:
        self.set_interval(0.12, self._tick_spinner)

    def _tick_spinner(self) -> None:
        self._spinner_idx = (self._spinner_idx + 1) % len(_SPINNERS)
        spinner_char = _SPINNERS[self._spinner_idx]
        now = time.monotonic()
        for name, status in self.agent_statuses.items():
            if status == "running" and name in self._lines:
                elapsed = ""
                if name in self._start_times:
                    elapsed = f"  {now - self._start_times[name]:.1f}s"
                label = name.capitalize() if name in _NODE_NAMES else name
                self._lines[name].update(f"  {spinner_char}  {label}{elapsed}")

    def watch_agent_statuses(self, statuses: dict[str, str]) -> None:
        for name, status in statuses.items():
            if name == "browse" and status == "running":
                self._browse_counter += 1
                label = f"browse[{self._browse_counter}]"
                line = Static(f"  ◌  {label}", id=_safe_id(label), classes="agent-row agent-icon-waiting")
                self._lines[label] = line
                self.mount(line, before=self._lines.get("research"))
            
            # Start time tracking
            if status == "running" and name not in self._start_times:
                self._start_times[name] = time.monotonic()

            if name in self._lines and status != "running": # running handled by tick
                label = name.capitalize() if name in _NODE_NAMES else name
                if status == "waiting":
                    self._lines[name].update(f"  ◌  {label}")
                    self._lines[name].remove_class("agent-icon-done", "agent-icon-error", "agent-icon-running")
                    self._lines[name].add_class("agent-icon-waiting")
                elif status == "done":
                    self._lines[name].update(f"  ✓  {label}")
                    self._lines[name].remove_class("agent-icon-waiting", "agent-icon-error", "agent-icon-running")
                    self._lines[name].add_class("agent-icon-done")
                elif status == "error":
                    self._lines[name].update(f"  ✗  {label}")
                    self._lines[name].remove_class("agent-icon-waiting", "agent-icon-done", "agent-icon-running")
                    self._lines[name].add_class("agent-icon-error")
            elif name in self._lines and status == "running":
                self._lines[name].remove_class("agent-icon-waiting", "agent-icon-done", "agent-icon-error")
                self._lines[name].add_class("agent-icon-running")

    def reset(self) -> None:
        self._browse_counter = 0
        self._start_times.clear()
        for key, line in list(self._lines.items()):
            if key.startswith("browse["):
                try:
                    line.remove()
                except Exception:
                    pass
                del self._lines[key]
            else:
                line.update(f"  ◌  {key.capitalize()}")
                line.remove_class("agent-icon-done", "agent-icon-error", "agent-icon-running")
                line.add_class("agent-icon-waiting")
