from __future__ import annotations


def choose_strategy(goal: str) -> str:
    normalized = goal.lower()
    if any(term in normalized for term in [" vs ", "compare", "comparison", "best"]):
        return "comparison"
    if "github" in normalized or "repo" in normalized or "open-source" in normalized:
        return "github_research"
    if "job" in normalized or "internship" in normalized or "hiring" in normalized:
        return "opportunity_search"
    if "docs" in normalized or "documentation" in normalized or "api" in normalized:
        return "technical_review"
    if "competitor" in normalized or "market" in normalized:
        return "market_research"
    return "general_research"


def strategy_queries(goal: str, strategy: str) -> list[str]:
    if strategy == "comparison":
        return [goal, f"{goal} official docs", f"{goal} GitHub"]
    if strategy == "github_research":
        return [goal, f"{goal} site:github.com", f"{goal} stars issues recent activity"]
    if strategy == "opportunity_search":
        return [goal, f"{goal} application requirements", f"{goal} recent openings"]
    if strategy == "technical_review":
        return [goal, f"{goal} official documentation", f"{goal} examples"]
    if strategy == "market_research":
        return [goal, f"{goal} pricing competitors", f"{goal} reviews"]
    return [goal]
