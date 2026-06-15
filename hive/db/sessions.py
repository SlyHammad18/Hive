import asyncio
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite
import platformdirs

from hive.core.log import get_logger
from hive.core.tools.citations import Citation

_log = get_logger("sessions")


@dataclass
class Message:
    role: str
    agent_name: str | None
    content: str
    timestamp: datetime


@dataclass
class SessionInfo:
    id: str
    created_at: datetime
    query: str
    provider: str
    model: str
    messages: list[Message]
    citations: list[Citation]
    token_usage: dict[str, int]
    cost_usd: float


def _db_path() -> Path:
    return Path(platformdirs.user_data_dir("hive", ensure_exists=True)) / "sessions.db"


_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    query TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT '',
    model TEXT NOT NULL DEFAULT '',
    token_usage_json TEXT NOT NULL DEFAULT '{}',
    cost_usd REAL NOT NULL DEFAULT 0.0
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    agent_name TEXT,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
CREATE TABLE IF NOT EXISTS citations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    "index" INTEGER NOT NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    snippet TEXT NOT NULL,
    agent TEXT NOT NULL DEFAULT '',
    timestamp TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
"""


def get_connection() -> sqlite3.Connection:
    db_path = _db_path()
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(_TABLE_DDL)
    conn.commit()
    return conn


async def get_async_connection() -> aiosqlite.Connection:
    db_path = _db_path()
    conn = await aiosqlite.connect(str(db_path))
    conn.row_factory = aiosqlite.Row
    await conn.executescript(_TABLE_DDL)
    await conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Async write queue — non-blocking writes for the TUI
# ---------------------------------------------------------------------------

_write_queue: asyncio.Queue | None = None
_write_worker_task: asyncio.Task[None] | None = None

_SENTINEL: tuple[str, None] = ("__SHUTDOWN__", None)
_shutting_down: bool = False


def _get_queue() -> asyncio.Queue:
    global _write_queue
    if _write_queue is None:
        _write_queue = asyncio.Queue()
    return _write_queue


async def _write_worker_loop() -> None:
    conn = await get_async_connection()
    try:
        while True:
            item = await _get_queue().get()
            if item is _SENTINEL:
                _get_queue().task_done()
                _log.debug("Write worker received sentinel, shutting down")
                break
            sql, params = item
            try:
                await conn.execute(sql, params)
                await conn.commit()
            except Exception as exc:
                _log.error("Write worker error: %s", exc, exc_info=True)
            finally:
                _get_queue().task_done()
    except asyncio.CancelledError:
        _log.warning("Write worker was cancelled — pending items may be lost (queue size: %s)", _get_queue().qsize())
    finally:
        await conn.close()
        _log.debug("Write worker connection closed")


def _ensure_worker() -> None:
    global _write_worker_task
    if _shutting_down:
        _log.warning("_ensure_worker called during shutdown — refusing to create new worker")
        return
    if _write_worker_task is None or _write_worker_task.done():
        _write_worker_task = asyncio.create_task(_write_worker_loop())
        _log.debug("Write worker task created")


def reset_queue() -> None:
    global _write_queue, _write_worker_task
    _log.debug("reset_queue called")
    if _write_worker_task is not None and not _write_worker_task.done():
        _write_worker_task.cancel()
    _write_queue = None
    _write_worker_task = None


async def flush() -> None:
    if _write_queue is not None:
        _log.debug("Flushing write queue (size: %s)", _write_queue.qsize())
        await _write_queue.join()


async def shutdown() -> None:
    global _write_queue, _write_worker_task, _shutting_down
    _shutting_down = True
    _log.info("shutdown: draining write queue...")
    if _write_queue is not None:
        qsize = _write_queue.qsize()
        _log.info("shutdown: queue size before drain: %s", qsize)
        await _write_queue.put(_SENTINEL)
    if _write_worker_task is not None and not _write_worker_task.done():
        try:
            await _write_worker_task
        except asyncio.CancelledError:
            _log.warning("shutdown: write worker was cancelled during drain")
    else:
        _log.debug("shutdown: write worker already done or None")
    _write_queue = None
    _write_worker_task = None
    _log.info("shutdown complete")


async def _enqueue(sql: str, *params: Any) -> None:
    if _shutting_down:
        _log.warning("_enqueue called during shutdown — dropping write: %s", sql[:80])
        return
    _ensure_worker()
    await _get_queue().put((sql, params))


# ---------------------------------------------------------------------------
# Session CRUD
# ---------------------------------------------------------------------------


async def create_session(
    session_id: str,
    query: str,
    provider: str = "",
    model: str = "",
    token_usage: dict[str, int] | None = None,
    cost_usd: float = 0.0,
) -> None:
    created_at = datetime.now(timezone.utc).isoformat()
    token_json = json.dumps(token_usage or {})
    await _enqueue(
        "INSERT INTO sessions (id, created_at, query, provider, model, token_usage_json, cost_usd) VALUES (?, ?, ?, ?, ?, ?, ?)",
        session_id,
        created_at,
        query,
        provider,
        model,
        token_json,
        cost_usd,
    )
    _log.debug("Queued create_session %s", session_id)


async def save_message(
    session_id: str,
    role: str,
    content: str,
    agent_name: str | None = None,
    timestamp: datetime | None = None,
) -> None:
    ts = (timestamp or datetime.now(timezone.utc)).isoformat()
    await _enqueue(
        "INSERT INTO messages (session_id, role, agent_name, content, timestamp) VALUES (?, ?, ?, ?, ?)",
        session_id,
        role,
        agent_name,
        content,
        ts,
    )
    _log.debug("Queued save_message for session %s", session_id)


async def save_citation(session_id: str, citation: Citation) -> None:
    ts = citation.timestamp.isoformat() if isinstance(citation.timestamp, datetime) else str(citation.timestamp)
    await _enqueue(
        'INSERT INTO citations (session_id, "index", url, title, snippet, agent, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)',
        session_id,
        citation.index,
        citation.url,
        citation.title,
        citation.snippet,
        citation.agent,
        ts,
    )
    _log.debug("Queued save_citation for session %s", session_id)


async def update_session(
    session_id: str,
    token_usage: dict[str, int] | None = None,
    cost_usd: float | None = None,
) -> None:
    token_json = json.dumps(token_usage) if token_usage else None
    if token_json is not None and cost_usd is not None:
        await _enqueue(
            "UPDATE sessions SET token_usage_json = ?, cost_usd = ? WHERE id = ?",
            token_json,
            cost_usd,
            session_id,
        )
    elif token_json is not None:
        await _enqueue("UPDATE sessions SET token_usage_json = ? WHERE id = ?", token_json, session_id)
    elif cost_usd is not None:
        await _enqueue("UPDATE sessions SET cost_usd = ? WHERE id = ?", cost_usd, session_id)


async def delete_session(session_id: str) -> None:
    await _enqueue("DELETE FROM messages WHERE session_id = ?", session_id)
    await _enqueue("DELETE FROM citations WHERE session_id = ?", session_id)
    await _enqueue("DELETE FROM sessions WHERE id = ?", session_id)
    _log.debug("Queued delete_session %s", session_id)


async def list_sessions() -> list[SessionInfo]:
    conn = await get_async_connection()
    try:
        cursor = await conn.execute(
            "SELECT id, created_at, query, provider, model, token_usage_json, cost_usd FROM sessions ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        result: list[SessionInfo] = []
        for row in rows:
            result.append(
                SessionInfo(
                    id=row["id"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    query=row["query"],
                    provider=row["provider"],
                    model=row["model"],
                    messages=[],
                    citations=[],
                    token_usage=json.loads(row["token_usage_json"]),
                    cost_usd=row["cost_usd"],
                )
            )
        return result
    finally:
        await conn.close()


async def load_session(session_id: str) -> SessionInfo | None:
    conn = await get_async_connection()
    try:
        cursor = await conn.execute(
            "SELECT id, created_at, query, provider, model, token_usage_json, cost_usd FROM sessions WHERE id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None

        msg_cur = await conn.execute(
            "SELECT role, agent_name, content, timestamp FROM messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        )
        msg_rows = await msg_cur.fetchall()
        messages = [
            Message(
                role=m["role"],
                agent_name=m["agent_name"],
                content=m["content"],
                timestamp=datetime.fromisoformat(m["timestamp"]),
            )
            for m in msg_rows
        ]

        cit_cur = await conn.execute(
            'SELECT "index", url, title, snippet, agent, timestamp FROM citations WHERE session_id = ? ORDER BY "index" ASC',
            (session_id,),
        )
        cit_rows = await cit_cur.fetchall()
        citations = [
            Citation(
                index=c["index"],
                url=c["url"],
                title=c["title"],
                snippet=c["snippet"],
                agent=c["agent"],
                timestamp=datetime.fromisoformat(c["timestamp"]),
            )
            for c in cit_rows
        ]

        return SessionInfo(
            id=row["id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            query=row["query"],
            provider=row["provider"],
            model=row["model"],
            messages=messages,
            citations=citations,
            token_usage=json.loads(row["token_usage_json"]),
            cost_usd=row["cost_usd"],
        )
    finally:
        await conn.close()
