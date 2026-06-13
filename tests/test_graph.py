import sqlite3
import typing

import pytest

from hive.core.graph.graph import _build_graph, compile_graph, compile_graph_async
from hive.core.graph.state import BrowserResult, CritiqueResult, HiveState, TokenUsage


@pytest.fixture(autouse=True)
def clear_tavily_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)


@pytest.fixture
def mem_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    yield conn
    conn.close()


def test_graph_compiles(mem_conn: sqlite3.Connection) -> None:
    app = compile_graph(connection=mem_conn)
    assert app is not None


@pytest.mark.asyncio
async def test_graph_compiles_async() -> None:
    import aiosqlite
    conn = await aiosqlite.connect(":memory:")
    try:
        app = await compile_graph_async(connection=conn)
        assert app is not None
    finally:
        await conn.close()


def test_graph_runs_stub_pipeline(mem_conn: sqlite3.Connection) -> None:
    app = compile_graph(connection=mem_conn)
    result = app.invoke(
        {"query": "test query"},
        {"configurable": {"thread_id": "test-1"}},
    )
    assert result["query"] == "test query"
    assert len(result["plan"]) >= 2
    assert len(result["browser_results"]) >= 2
    assert "research_notes" in result and result["research_notes"]
    assert "synthesis" in result and result["synthesis"]
    assert result["critique"] is not None
    assert result["critique"].confidence == 0.9


def test_graph_ends_after_one_pass(mem_conn: sqlite3.Connection) -> None:
    app = compile_graph(connection=mem_conn)
    result = app.invoke(
        {"query": "test query"},
        {"configurable": {"thread_id": "test-2"}},
    )
    assert result["iteration"] >= 1


def test_graph_builds_without_compiling() -> None:
    graph = _build_graph()
    assert graph is not None


def test_graph_state_schema() -> None:
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
