from __future__ import annotations

import asyncio

from ai_decision_os.answer import AnswerAgent


def test_answer_agent_falls_back_without_llm() -> None:
    answer = asyncio.run(
        AnswerAgent().create_answer(
            "How can MCP be used?",
            [
                {
                    "tool": "search_web",
                    "data": [
                        {
                            "title": "MCP docs",
                            "url": "https://modelcontextprotocol.io",
                            "snippet": "MCP connects AI apps to tools, data sources, and workflows.",
                        }
                    ],
                }
            ],
            [{"title": "MCP docs", "url": "https://modelcontextprotocol.io"}],
        )
    )

    assert "Answer to: How can MCP be used?" in answer
    assert "MCP connects AI apps" in answer
