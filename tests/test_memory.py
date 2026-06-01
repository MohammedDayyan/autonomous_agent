from __future__ import annotations

import asyncio

from ai_decision_os.tools.memory import MemoryStore


def test_memory_store_saves_and_searches(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite3")

    saved = asyncio.run(store.save_memory("research agents", "saved report"))
    rows = asyncio.run(store.search_memory("agents"))

    assert saved["id"] == 1
    assert rows[0]["task"] == "research agents"
    assert rows[0]["result"] == "saved report"
