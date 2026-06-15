import uuid
from datetime import datetime, timezone

import aiosqlite
import pytest

from hive.core.tools.citations import Citation
from hive.db import sessions as db


@pytest.fixture(autouse=True)
def temp_db(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "test_sessions.db"
    monkeypatch.setattr(db, "_db_path", lambda: db_path)


@pytest.fixture(autouse=True)
def fresh_queue() -> None:
    db.reset_queue()
    yield
    db.reset_queue()


@pytest.mark.asyncio
async def test_create_and_load() -> None:
    sid = str(uuid.uuid4())
    await db.create_session(
        session_id=sid,
        query="test query",
        provider="openai",
        model="gpt-4o",
        token_usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        cost_usd=0.002,
    )
    await db._get_queue().join()

    s = await db.load_session(sid)
    assert s is not None
    assert s.id == sid
    assert s.query == "test query"
    assert s.provider == "openai"
    assert s.model == "gpt-4o"
    assert s.token_usage["total_tokens"] == 150
    assert s.cost_usd == 0.002
    assert s.messages == []
    assert s.citations == []


@pytest.mark.asyncio
async def test_save_and_load_messages() -> None:
    sid = str(uuid.uuid4())
    await db.create_session(session_id=sid, query="msg test")
    now = datetime.now(timezone.utc)
    await db.save_message(sid, "user", "Hello", timestamp=now)
    await db.save_message(sid, "assistant", "Hi there", agent_name="Synthesizer", timestamp=now)
    await db._get_queue().join()

    s = await db.load_session(sid)
    assert s is not None
    assert len(s.messages) == 2
    assert s.messages[0].role == "user"
    assert s.messages[0].content == "Hello"
    assert s.messages[0].agent_name is None
    assert s.messages[1].role == "assistant"
    assert s.messages[1].content == "Hi there"
    assert s.messages[1].agent_name == "Synthesizer"


@pytest.mark.asyncio
async def test_save_and_load_citations() -> None:
    sid = str(uuid.uuid4())
    await db.create_session(session_id=sid, query="cite test")
    cit = Citation(
        index=1, url="https://example.com", title="Example", snippet="Some text", agent="Browser"
    )
    await db.save_citation(sid, cit)
    await db._get_queue().join()

    s = await db.load_session(sid)
    assert s is not None
    assert len(s.citations) == 1
    assert s.citations[0].url == "https://example.com"
    assert s.citations[0].title == "Example"
    assert s.citations[0].snippet == "Some text"
    assert s.citations[0].agent == "Browser"
    assert s.citations[0].index == 1


@pytest.mark.asyncio
async def test_list_sessions_ordered() -> None:
    id_a = str(uuid.uuid4())
    id_b = str(uuid.uuid4())
    await db.create_session(session_id=id_a, query="first")
    await db.create_session(session_id=id_b, query="second")
    await db._get_queue().join()

    sessions = await db.list_sessions()
    assert len(sessions) >= 2
    idx_a = next(i for i, s in enumerate(sessions) if s.id == id_a)
    idx_b = next(i for i, s in enumerate(sessions) if s.id == id_b)
    assert idx_b < idx_a


@pytest.mark.asyncio
async def test_update_session() -> None:
    sid = str(uuid.uuid4())
    await db.create_session(session_id=sid, query="update test")
    await db._get_queue().join()
    await db.update_session(sid, token_usage={"total_tokens": 200}, cost_usd=0.005)
    await db._get_queue().join()

    s = await db.load_session(sid)
    assert s is not None
    assert s.token_usage["total_tokens"] == 200
    assert s.cost_usd == 0.005


@pytest.mark.asyncio
async def test_delete_session_cascades() -> None:
    sid = str(uuid.uuid4())
    await db.create_session(session_id=sid, query="delete test")
    await db.save_message(sid, "user", "msg")
    await db._get_queue().join()

    await db.delete_session(sid)
    await db._get_queue().join()

    assert await db.load_session(sid) is None


@pytest.mark.asyncio
async def test_full_round_trip() -> None:
    sid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await db.create_session(
        session_id=sid,
        query="round trip",
        provider="anthropic",
        model="claude-sonnet-4-6",
        token_usage={"prompt_tokens": 500, "completion_tokens": 200, "total_tokens": 700},
        cost_usd=0.015,
    )
    await db.save_message(sid, "user", "What is AI?", timestamp=now)
    await db.save_message(
        sid, "assistant", "AI stands for...", agent_name="Synthesizer", timestamp=now
    )
    cit = Citation(
        index=1,
        url="https://ai.org",
        title="AI Overview",
        snippet="AI is...",
        agent="Browser",
    )
    await db.save_citation(sid, cit)
    await db._get_queue().join()

    loaded = await db.load_session(sid)
    assert loaded is not None
    assert loaded.id == sid
    assert loaded.query == "round trip"
    assert loaded.provider == "anthropic"
    assert loaded.model == "claude-sonnet-4-6"
    assert loaded.token_usage == {"prompt_tokens": 500, "completion_tokens": 200, "total_tokens": 700}
    assert loaded.cost_usd == 0.015
    assert len(loaded.messages) == 2
    assert len(loaded.citations) == 1
    assert loaded.citations[0].url == "https://ai.org"


@pytest.mark.asyncio
async def test_load_missing() -> None:
    assert await db.load_session("nonexistent") is None


@pytest.mark.asyncio
async def test_list_empty() -> None:
    sessions = await db.list_sessions()
    assert isinstance(sessions, list)


@pytest.mark.asyncio
async def test_langgraph_checkpointer_integration() -> None:
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    conn = await db.get_async_connection()
    try:
        checkpointer = AsyncSqliteSaver(conn)
        assert checkpointer is not None
    finally:
        await conn.close()
