from __future__ import annotations

from typing import Any

from ai_decision_os.llm import GroqClient
from ai_decision_os.tools.report import render_final_answer


ANSWER_SYSTEM_PROMPT = """You are the Answer Agent for AI Decision OS.
Use only the supplied research observations and source scores.
Return a concise final answer for the user, not a report.
Prefer 3 to 6 bullets or short paragraphs.
Mention uncertainty if the evidence is weak.
Do not include raw tool logs, JSON, or internal planning details.
"""


class AnswerAgent:
    def __init__(self, groq: GroqClient | None = None) -> None:
        self.groq = groq

    async def create_answer(
        self,
        goal: str,
        observations: list[dict[str, Any]],
        source_scores: list[dict[str, object]],
    ) -> str:
        fallback = render_final_answer(goal, observations, source_scores)
        if self.groq is None:
            return fallback

        try:
            research_context = _compact_research_context(observations, source_scores)
            answer = await self.groq.complete_text(
                ANSWER_SYSTEM_PROMPT,
                f"User question:\n{goal}\n\nResearch evidence:\n{research_context}",
            )
            return answer or fallback
        except Exception:
            return fallback


def _compact_research_context(
    observations: list[dict[str, Any]],
    source_scores: list[dict[str, object]],
    max_chars: int = 9000,
) -> str:
    parts: list[str] = []
    if source_scores:
        parts.append("Top sources:")
        for source in source_scores[:5]:
            parts.append(
                f"- {source.get('title') or 'Source'} "
                f"({source.get('url') or source.get('domain') or 'no url'}), "
                f"confidence={source.get('confidence', 'n/a')}"
            )
    parts.append("Observations:")
    for observation in observations:
        tool = observation.get("tool", "tool")
        data = observation.get("data")
        parts.append(f"\nTool: {tool}")
        parts.append(_compact_data(data))
        current = "\n".join(parts)
        if len(current) >= max_chars:
            return current[:max_chars]
    return "\n".join(parts)[:max_chars]


def _compact_data(data: Any) -> str:
    if isinstance(data, list):
        lines: list[str] = []
        for item in data[:5]:
            if not isinstance(item, dict):
                lines.append(str(item))
                continue
            title = item.get("title") or item.get("repo") or item.get("url") or "Result"
            url = item.get("url")
            snippet = item.get("snippet") or item.get("description") or ""
            lines.append(f"- {title}: {snippet} {url or ''}".strip())
        return "\n".join(lines)
    if isinstance(data, dict):
        if data.get("error"):
            return f"Error: {data['error']}"
        title = data.get("title") or data.get("repo") or data.get("url") or "Result"
        text = data.get("text") or data.get("description") or data.get("snippet") or data
        return f"- {title}: {text}"
    return str(data)
