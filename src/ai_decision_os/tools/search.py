from __future__ import annotations

import os
from urllib.parse import quote_plus

import httpx
from dotenv import load_dotenv


async def search_web(query: str, limit: int = 5) -> list[dict[str, str]]:
    """Search with Tavily when configured, then fall back to DuckDuckGo Instant Answer."""
    load_dotenv()
    tavily_api_key = _clean_api_key(os.getenv("TAVILY_API_KEY"))
    if tavily_api_key:
        return await _search_tavily(query, limit, tavily_api_key)

    return await _search_duckduckgo(query, limit)


def tavily_configured() -> bool:
    load_dotenv()
    return bool(_clean_api_key(os.getenv("TAVILY_API_KEY")))


def _clean_api_key(value: str | None) -> str:
    return (value or "").strip().strip('"').strip("'").strip()


async def _search_tavily(query: str, limit: int, api_key: str) -> list[dict[str, str]]:
    url = "https://api.tavily.com/search"
    payload = {
        "query": query,
        "search_depth": "basic",
        "include_answer": True,
        "include_raw_content": False,
        "max_results": limit,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
        data = response.json()
    except Exception as exc:
        print(f"Tavily search failed for query={query!r}: {exc}", flush=True)
        return [
            {
                "title": "Tavily search unavailable",
                "url": f"https://duckduckgo.com/?q={quote_plus(query)}",
                "snippet": f"Tavily search failed: {exc}",
            }
        ]

    results: list[dict[str, str]] = []
    answer = data.get("answer")
    if isinstance(answer, str) and answer.strip():
        results.append(
            {
                "title": "Tavily answer",
                "url": "https://tavily.com",
                "snippet": answer.strip(),
            }
        )

    for item in data.get("results", []):
        if len(results) >= limit:
            break
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "Untitled result")
        url_value = str(item.get("url") or "")
        content = str(item.get("content") or item.get("snippet") or "")
        score = item.get("score")
        score_text = f" Relevance score: {score}." if score is not None else ""
        results.append(
            {
                "title": title,
                "url": url_value,
                "snippet": f"{content}{score_text}".strip(),
            }
        )

    if not results:
        results.append(
            {
                "title": "No Tavily results",
                "url": f"https://duckduckgo.com/?q={quote_plus(query)}",
                "snippet": "Tavily returned no results for this query.",
            }
        )
    return results[:limit]


async def _search_duckduckgo(query: str, limit: int) -> list[dict[str, str]]:
    url = "https://api.duckduckgo.com/"
    params = {"q": query, "format": "json", "no_redirect": "1", "no_html": "1"}
    results: list[dict[str, str]] = []

    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
        payload = response.json()
        abstract_url = payload.get("AbstractURL")
        abstract = payload.get("AbstractText")
        if abstract_url and abstract:
            results.append(
                {"title": payload.get("Heading") or query, "url": abstract_url, "snippet": abstract}
            )
        for topic in payload.get("RelatedTopics", []):
            if len(results) >= limit:
                break
            if "FirstURL" in topic and "Text" in topic:
                results.append(
                    {
                        "title": topic["Text"].split(" - ")[0][:120],
                        "url": topic["FirstURL"],
                        "snippet": topic["Text"],
                    }
                )
    except Exception as exc:
        results.append(
            {
                "title": "Search unavailable",
                "url": f"https://duckduckgo.com/?q={quote_plus(query)}",
                "snippet": f"Live search failed: {exc}",
            }
        )

    if not results:
        results.append(
            {
                "title": "Open web search",
                "url": f"https://duckduckgo.com/?q={quote_plus(query)}",
                "snippet": "No instant-answer results returned. Open this URL for manual review.",
            }
        )
    return results[:limit]
