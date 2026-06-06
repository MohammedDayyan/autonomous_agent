from __future__ import annotations

import os
from typing import Literal
from urllib.parse import quote_plus

import httpx
from dotenv import load_dotenv


async def search_web(query: str, limit: int = 5) -> list[dict[str, str]]:
    """Search with Tavily when configured, then fall back to DuckDuckGo Instant Answer."""
    load_dotenv()
    tavily_api_key = _tavily_api_key()
    if tavily_api_key:
        return await _search_tavily(query, limit, tavily_api_key)

    return await _search_duckduckgo(query, limit)


async def search_diagnostics(query: str = "Model Context Protocol") -> dict[str, object]:
    results = await search_web(query, limit=3)
    provider = _detect_provider(results)
    return {
        "query": query,
        "provider": provider,
        "tavily_configured": tavily_configured(),
        "first_result_title": results[0]["title"] if results else None,
        "first_result_url": results[0]["url"] if results else None,
        "results": results,
    }


def _detect_provider(results: list[dict[str, str]]) -> Literal["tavily", "duckduckgo", "unknown"]:
    if not results:
        return "unknown"
    first = results[0]
    title = first.get("title", "").lower()
    url = first.get("url", "").lower()
    snippet = first.get("snippet", "").lower()
    if "tavily" in title or "tavily.com" in url or "relevance score:" in snippet:
        return "tavily"
    if "duckduckgo.com" in url or title in {"open web search", "search unavailable"}:
        return "duckduckgo"
    return "unknown"


async def tavily_diagnostics() -> dict[str, object]:
    load_dotenv()
    tavily_api_key = _tavily_api_key()
    if not tavily_api_key:
        return {
            "configured": False,
            "ok": False,
            "reason": "TAVILY_API_KEY is not set.",
            "accepted_env_vars": ["TAVILY_API_KEY", "TRAVILY_API_KEY"],
            "misspelled_key_present": bool(_clean_api_key(os.getenv("TRAVILY_API_KEY"))),
        }

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            response = await client.get(
                "https://api.tavily.com/usage",
                headers={"Authorization": f"Bearer {tavily_api_key}"},
            )
        detail = ""
        if response.status_code >= 400:
            detail = response.text[:300]
        return {
            "configured": True,
            "ok": response.status_code == 200,
            "status_code": response.status_code,
            "env_var": _tavily_api_key_name(),
            "key_prefix": tavily_api_key[:8],
            "detail": detail,
        }
    except Exception as exc:
        return {
            "configured": True,
            "ok": False,
            "env_var": _tavily_api_key_name(),
            "key_prefix": tavily_api_key[:8],
            "error": str(exc),
        }


def tavily_configured() -> bool:
    load_dotenv()
    return bool(_tavily_api_key())


def _clean_api_key(value: str | None) -> str:
    return (value or "").strip().strip('"').strip("'").strip()


def _tavily_api_key() -> str:
    return _clean_api_key(os.getenv("TAVILY_API_KEY")) or _clean_api_key(os.getenv("TRAVILY_API_KEY"))


def _tavily_api_key_name() -> str | None:
    if _clean_api_key(os.getenv("TAVILY_API_KEY")):
        return "TAVILY_API_KEY"
    if _clean_api_key(os.getenv("TRAVILY_API_KEY")):
        return "TRAVILY_API_KEY"
    return None


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
                "url": "https://tavily.com",
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
                "snippet": f"{answer.strip()} Provider: Tavily.",
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
                "snippet": f"{content}{score_text} Provider: Tavily.".strip(),
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
