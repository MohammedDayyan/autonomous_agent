from __future__ import annotations

from ai_decision_os.tools.report import render_final_answer


def test_render_final_answer_is_concise() -> None:
    answer = render_final_answer(
        "How can MCP be used?",
        [
            {
                "tool": "search_web",
                "data": [
                    {
                        "title": "Model Context Protocol",
                        "url": "https://modelcontextprotocol.io",
                        "snippet": "MCP connects AI applications to tools, data sources, and workflows through a standard protocol.",
                    }
                ],
            }
        ],
        [{"title": "MCP docs", "url": "https://modelcontextprotocol.io"}],
    )

    assert "Answer to: How can MCP be used?" in answer
    assert "MCP connects AI applications" in answer
    assert "Most useful sources:" in answer
    assert "## Findings" not in answer


def test_render_final_answer_synthesizes_cybersecurity_tools() -> None:
    answer = render_final_answer(
        "Find all the cybersecurity tools",
        [
            {
                "tool": "search_web",
                "data": [
                    {
                        "title": "Top cybersecurity tools",
                        "snippet": "Cybersecurity tools help protect networks and systems from cyber threats...",
                    }
                ],
            }
        ],
        [],
    )

    assert "There is no single finite list" in answer
    assert "Network protection" in answer
    assert "Endpoint protection" in answer
    assert "..." not in answer
