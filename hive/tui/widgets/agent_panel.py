from textual.reactive import reactive
from textual.widgets import Tree

_NODE_NAMES = ["plan", "browse", "research", "synthesize", "critique"]
_STATUS_ICONS = {
    "waiting": "◌",
    "running": "↻",
    "done": "✓",
    "error": "✗",
}


class AgentPanel(Tree[dict]):
    agent_statuses: reactive[dict[str, str]] = reactive({}, always_update=True)

    def __init__(self) -> None:
        super().__init__("Orchestrator")
        self._nodes: dict[str, Tree[dict].NodeType] = {}
        self._browse_counter = 0

    def on_mount(self) -> None:
        self.root.expand()
        for name in _NODE_NAMES:
            node = self.root.add(f"{_STATUS_ICONS['waiting']} {name.capitalize()}", data={"agent": name, "status": "waiting"})
            self._nodes[name] = node

    def watch_agent_statuses(self, statuses: dict[str, str]) -> None:
        for name, status in statuses.items():
            if name == "browse" and status == "running":
                self._browse_counter += 1
                count = self._browse_counter
                child = self._nodes["browse"].add(
                    f"{_STATUS_ICONS['running']} browse[{count}]",
                    data={"agent": f"browse[{count}]", "status": "running"},
                )
                self._nodes[f"browse[{count}]"] = child
            elif name.startswith("browse[") and name in self._nodes:
                node = self._nodes[name]
                icon = _STATUS_ICONS.get(status, "◌")
                node.label = f"{icon} {name}"
                node.data["status"] = status
            elif name in self._nodes:
                node = self._nodes[name]
                icon = _STATUS_ICONS.get(status, "◌")
                node.label = f"{icon} {name.capitalize()}"
                node.data["status"] = status

    def reset(self) -> None:
        self._browse_counter = 0
        for name, node in list(self._nodes.items()):
            if name.startswith("browse["):
                try:
                    node.remove()
                except Exception:
                    pass
                del self._nodes[name]
            else:
                icon = _STATUS_ICONS["waiting"]
                node.label = f"{icon} {name.capitalize()}"
                node.data["status"] = "waiting"
