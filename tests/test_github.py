from __future__ import annotations

import httpx
import pytest

from ai_decision_os.tools import github


def test_normalize_repo_accepts_urls_and_slugs() -> None:
    assert github._normalize_repo("https://github.com/google-research/google-research/") == (
        "google-research/google-research"
    )
    assert github._normalize_repo("github.com/langchain-ai/langgraph") == "langchain-ai/langgraph"
    assert github._normalize_repo(" langchain-ai/langchain ") == "langchain-ai/langchain"


@pytest.mark.anyio
async def test_search_repo_prefers_exact_name_match() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "items": [
                    {"name": "not-it", "full_name": "example/not-it"},
                    {"name": "google-research", "full_name": "google-research/google-research"},
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await github._search_repo(client, "google/google-research") == "google-research/google-research"
