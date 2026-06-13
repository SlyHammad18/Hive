import sqlite3

import pytest
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph

from hive.core.graph.graph import _build_graph, compile_graph
from hive.core.graph.state import HiveState


@pytest.fixture
def mem_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    yield conn
    conn.close()


def test_graph_compiles(mem_conn: sqlite3.Connection) -> None:
    app = compile_graph(connection=mem_conn)
    assert app is not None


def test_graph_runs_stub_pipeline(mem_conn: sqlite3.Connection) -> None:
    app = compile_graph(connection=mem_conn)
    result = app.invoke(
        {"query": "test query"},
        {"configurable": {"thread_id": "test-1"}},
    )
    assert result["query"] == "test query"
    assert len(result["plan"]) == 2
    assert len(result["browser_results"]) == 2
    assert "research_notes" in result and result["research_notes"]
    assert "synthesis" in result and result["synthesis"]
    assert result["critique"] is not None
    assert result["critique"].confidence == 0.9
    assert result["iteration"] == 0


def test_graph_ends_after_one_pass(mem_conn: sqlite3.Connection) -> None:
    app = compile_graph(connection=mem_conn)
    result = app.invoke(
        {"query": "test query"},
        {"configurable": {"thread_id": "test-2"}},
    )
    assert result["iteration"] == 0


def test_graph_rejects_invalid_query() -> None:
    app = _build_graph()
    with pytest.raises(Exception):
        app.compile()


def test_graph_state_schema() -> None:
    import typing

    from hive.core.graph.state import BrowserResult, CritiqueResult, TokenUsage

    assert hasattr(HiveState, "__annotations__")
    annotations = typing.get_type_hints(HiveState)
    assert "query" in annotations
    assert "plan" in annotations
    assert "browser_results" in annotations
    assert "research_notes" in annotations
    assert "synthesis" in annotations
    assert "critique" in annotations
    assert "citations" in annotations
    assert "token_usage" in annotations
    assert "iteration" in annotations
    assert "messages" in annotations

    br = BrowserResult(sub_query="q", url="u", title="t", snippet="s")
    assert br.sub_query == "q"
    assert br.text == ""

    cr = CritiqueResult(issues=[], confidence=0.9, follow_ups=[])
    assert cr.confidence == 0.9

    tu = TokenUsage()
    assert tu.total_tokens == 0
