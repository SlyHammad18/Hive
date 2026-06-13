from hive.core.graph.state import HiveState


def planner_node(state: HiveState) -> dict:
    return {
        "plan": ["sub-query 1", "sub-query 2"],
        "iteration": 0,
    }
