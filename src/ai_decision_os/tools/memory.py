from __future__ import annotations

import asyncio
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class MemoryStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task TEXT NOT NULL,
                    result TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    async def save_memory(self, task: str, result: str) -> dict[str, object]:
        return await asyncio.to_thread(self._save_memory_sync, task, result)

    def _save_memory_sync(self, task: str, result: str) -> dict[str, object]:
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO memories (task, result, created_at) VALUES (?, ?, ?)",
                (task, result, created_at),
            )
            lastrowid = cursor.lastrowid
        return {"id": lastrowid, "created_at": created_at}

    async def search_memory(self, query: str, limit: int = 5) -> list[dict[str, object]]:
        return await asyncio.to_thread(self._search_memory_sync, query, limit)

    def _search_memory_sync(self, query: str, limit: int) -> list[dict[str, object]]:
        pattern = f"%{query}%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, task, result, created_at
                FROM memories
                WHERE task LIKE ? OR result LIKE ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (pattern, pattern, limit),
            ).fetchall()
        return [
            {"id": row[0], "task": row[1], "result": row[2], "created_at": row[3]}
            for row in rows
        ]
