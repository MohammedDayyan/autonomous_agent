from __future__ import annotations

import os

import httpx


async def analyze_github_repo(repo: str) -> dict[str, object]:
    repo = _normalize_repo(repo)
    async with httpx.AsyncClient(timeout=20) as client:
        response = await _get_repo(client, repo)
        if response.status_code == 404:
            resolved = await _search_repo(client, repo)
            if resolved is not None:
                response = await _get_repo(client, resolved)
        response.raise_for_status()
    payload = response.json()
    return {
        "repo": payload["full_name"],
        "description": payload.get("description") or "",
        "stars": payload.get("stargazers_count", 0),
        "forks": payload.get("forks_count", 0),
        "language": payload.get("language") or "Unknown",
        "open_issues": payload.get("open_issues_count", 0),
        "url": payload["html_url"],
        "updated_at": payload.get("updated_at"),
    }


def _normalize_repo(repo: str) -> str:
    repo = repo.removeprefix("https://github.com/").removeprefix("http://github.com/")
    repo = repo.removeprefix("github.com/")
    return repo.strip().strip("/")


def _get_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "AIDecisionOS/0.1.0 (Reason-Research-Execute-Agent)"
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


async def _get_repo(client: httpx.AsyncClient, repo: str) -> httpx.Response:
    return await client.get(
        f"https://api.github.com/repos/{repo}",
        headers=_get_headers(),
    )


async def _search_repo(client: httpx.AsyncClient, repo: str) -> str | None:
    owner, _, name = repo.partition("/")
    queries = []
    if owner and name:
        queries.extend([f"{name} org:{owner}", name])
    else:
        queries.append(repo)

    for query in queries:
        response = await client.get(
            "https://api.github.com/search/repositories",
            params={"q": query, "sort": "stars", "order": "desc", "per_page": 5},
            headers=_get_headers(),
        )
        if response.status_code >= 400:
            continue
        items = response.json().get("items", [])
        if not items:
            continue
        exact_name_match = [
            item for item in items
            if name and str(item.get("name", "")).lower() == name.lower()
        ]
        best = exact_name_match[0] if exact_name_match else items[0]
        full_name = best.get("full_name")
        if isinstance(full_name, str) and "/" in full_name:
            return full_name
    return None


def _normalize_user(username: str) -> str:
    username = username.removeprefix("https://github.com/").removeprefix("http://github.com/")
    username = username.removeprefix("github.com/")
    return username.strip().strip("/")


async def list_user_repos(username: str) -> list[dict[str, object]]:
    """List public repositories for a GitHub user or organization."""
    username = _normalize_user(username)
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            f"https://api.github.com/users/{username}/repos",
            params={"sort": "updated", "per_page": 30},
            headers=_get_headers()
        )
        response.raise_for_status()
    payload = response.json()
    return [
        {
            "name": item["name"],
            "full_name": item["full_name"],
            "description": item.get("description") or "",
            "stars": item.get("stargazers_count", 0),
            "language": item.get("language") or "Unknown",
            "url": item["html_url"],
            "updated_at": item.get("updated_at"),
        }
        for item in payload
    ]
