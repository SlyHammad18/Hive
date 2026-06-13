import sqlite3
from pathlib import Path

import aiosqlite
import platformdirs


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
