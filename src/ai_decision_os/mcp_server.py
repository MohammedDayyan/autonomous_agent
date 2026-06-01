from __future__ import annotations

from functools import partial

from mcp.server.fastmcp import FastMCP

from ai_decision_os.config import load_settings
from ai_decision_os.tools.browser import extract_page as browser_extract_page
from ai_decision_os.tools.github import (
    analyze_github_repo as github_analyze_repo,
    list_user_repos as github_list_user_repos,
)
from ai_decision_os.tools.memory import MemoryStore
from ai_decision_os.tools.report import save_report as report_save_report
from ai_decision_os.tools.search import search_web as web_search

mcp = FastMCP("AI Decision OS")
settings = load_settings()
memory = MemoryStore(settings.memory_db)
save_report_to_dir = partial(report_save_report, settings.reports_dir)


@mcp.tool()
async def search_web(query: str, limit: int = 5) -> list[dict[str, str]]:
    """Search the public web for research material."""
    return await web_search(query, limit)


@mcp.tool()
async def extract_page(url: str, max_chars: int = 5000) -> dict[str, str]:
    """Extract readable text from a web page with Playwright."""
    return await browser_extract_page(url, max_chars)


@mcp.tool()
async def analyze_github_repo(repo: str) -> dict[str, object]:
    """Fetch GitHub repository metadata for owner/repo or a GitHub URL."""
    return await github_analyze_repo(repo)


@mcp.tool()
async def list_user_repos(username: str) -> list[dict[str, object]]:
    """List public repositories for a GitHub user or organization."""
    return await github_list_user_repos(username)


@mcp.tool()
async def save_report(filename: str, content: str) -> dict[str, str]:
    """Save a markdown report to the local reports directory."""
    return await save_report_to_dir(filename, content)


@mcp.tool()
async def save_memory(task: str, result: str) -> dict[str, object]:
    """Persist a task result in local SQLite memory."""
    return await memory.save_memory(task, result)


@mcp.tool()
async def search_memory(query: str, limit: int = 5) -> list[dict[str, object]]:
    """Search previous task memories."""
    return await memory.search_memory(query, limit)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
