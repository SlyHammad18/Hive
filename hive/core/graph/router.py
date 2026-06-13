from langgraph.graph import END

from hive.core.graph.state import HiveState


def should_continue(state: HiveState) -> str:
    critique = state.get("critique")
    iteration: int = state.get("iteration", 0)
    if critique is None:
        return END
    if critique.confidence < 0.6 and iteration < 2:
        return "plan"
    return END
