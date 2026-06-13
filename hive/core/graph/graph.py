import sqlite3

from langgraph.constants import Send
from langgraph.graph import END, StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver

from hive.core.graph.router import should_continue
from hive.core.graph.state import HiveState
from hive.core.nodes.planner import planner_node
from hive.core.nodes.browser import browser_node
from hive.core.nodes.researcher import researcher_node
from hive.core.nodes.synthesizer import synthesizer_node
from hive.core.nodes.critic import critic_node
from hive.db.sessions import get_connection


def _plan_to_browse(state: HiveState) -> list[Send]:
    return [Send("browse", {"sub_query": q}) for q in state.get("plan", [])]


def _build_graph() -> StateGraph:
    graph = StateGraph(HiveState)

    graph.add_node("plan", planner_node)
    graph.add_node("browse", browser_node)
    graph.add_node("research", researcher_node)
    graph.add_node("synthesize", synthesizer_node)
    graph.add_node("critique", critic_node)

    graph.set_entry_point("plan")
    graph.add_conditional_edges("plan", _plan_to_browse, ["browse"])
    graph.add_edge("browse", "research")
    graph.add_edge("research", "synthesize")
    graph.add_edge("synthesize", "critique")
    graph.add_conditional_edges(
        "critique",
        should_continue,
        {"plan": "plan", END: END},
    )

    return graph


def compile_graph(connection: sqlite3.Connection | None = None):
    conn = connection or get_connection()
    checkpointer = SqliteSaver(conn)
    graph = _build_graph()
    return graph.compile(checkpointer=checkpointer)
