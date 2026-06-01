from __future__ import annotations

from urllib.parse import urlparse


PRIMARY_HINTS = ("docs.", "github.com", "arxiv.org", "pypi.org", "readthedocs", "developer.")
LOWER_AUTHORITY_HINTS = ("medium.com", "dev.to", "reddit.com")


def score_source(goal: str, item: dict[str, object]) -> dict[str, object]:
    url = str(item.get("url") or "")
    title = str(item.get("title") or "")
    snippet = str(item.get("snippet") or item.get("content") or "")
    domain = urlparse(url).netloc.lower()
    haystack = f"{title} {snippet} {url}".lower()
    goal_terms = [term for term in goal.lower().replace("/", " ").split() if len(term) > 3]
    matches = sum(1 for term in goal_terms if term in haystack)

    authority = 0.55
    if any(hint in domain for hint in PRIMARY_HINTS):
        authority += 0.3
    if any(hint in domain for hint in LOWER_AUTHORITY_HINTS):
        authority -= 0.1

    relevance = min(1.0, 0.35 + (matches / max(len(goal_terms), 1)) * 0.65)
    confidence = round((authority * 0.45) + (relevance * 0.55), 2)

    return {
        "title": title or "Untitled source",
        "url": url,
        "domain": domain,
        "authority": round(max(0.0, min(authority, 1.0)), 2),
        "relevance": round(relevance, 2),
        "confidence": confidence,
        "reason": "Primary/official source signal." if authority >= 0.8 else "Useful supporting source.",
    }


def score_observations(goal: str, observations: list[dict[str, object]]) -> list[dict[str, object]]:
    scored: list[dict[str, object]] = []
    for observation in observations:
        data = observation.get("data")
        if not isinstance(data, list):
            continue
        for item in data:
            if isinstance(item, dict) and item.get("url"):
                scored.append(score_source(goal, item))
    return sorted(scored, key=lambda item: item["confidence"], reverse=True)
