from __future__ import annotations

import json
import os
import sys
from contextlib import AsyncExitStack
from io import TextIOWrapper
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import TextContent


class MCPToolClient:
    def __init__(self, cwd: Path | None = None) -> None:
        self.cwd = cwd or Path.cwd()
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self._errlog: TextIOWrapper | None = None

    async def __aenter__(self) -> MCPToolClient:
        self._stack = AsyncExitStack()
        self._errlog = open(os.devnull, "w", encoding="utf-8")
        server = StdioServerParameters(
            command=sys.executable,
            args=["-m", "ai_decision_os.mcp_server"],
            cwd=str(self.cwd),
        )
        read_stream, write_stream = await self._stack.enter_async_context(
            stdio_client(server, errlog=self._errlog)
        )
        self._session = await self._stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await self._session.initialize()
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self._stack is not None:
            await self._stack.aclose()
        if self._errlog is not None:
            self._errlog.close()
        self._stack = None
        self._session = None
        self._errlog = None

    async def call(self, name: str, **kwargs: Any) -> Any:
        if self._session is None:
            raise RuntimeError("MCPToolClient must be used as an async context manager.")

        result = await self._session.call_tool(name, kwargs)
        if result.isError:
            message = self._content_to_text(result.content)
            raise RuntimeError(message or f"MCP tool {name} failed")

        if result.structuredContent is not None:
            return result.structuredContent.get("result", result.structuredContent)

        text = self._content_to_text(result.content)
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    def _content_to_text(self, content: list[object]) -> str:
        parts: list[str] = []
        for item in content:
            if isinstance(item, TextContent):
                parts.append(item.text)
        return "\n".join(parts)
