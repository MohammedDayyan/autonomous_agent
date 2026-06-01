from __future__ import annotations

from ai_decision_os.models import ApprovalDecision


SAFE_TOOLS = {
    "search_web": "Reads public search results.",
    "extract_page": "Reads public page text.",
    "analyze_github_repo": "Reads public GitHub metadata.",
    "list_user_repos": "Reads public GitHub repositories for a user or organization.",
    "save_report": "Writes a markdown report inside the configured reports directory.",
    "save_memory": "Writes task memory to the local SQLite store.",
    "search_memory": "Reads prior local task memory.",
}


class ApprovalPolicy:
    def check(self, tool: str) -> ApprovalDecision:
        if tool in SAFE_TOOLS:
            return ApprovalDecision(tool=tool, approved=True, risk="safe", reason=SAFE_TOOLS[tool])
        return ApprovalDecision(
            tool=tool,
            approved=False,
            risk="needs_approval",
            reason="Unknown tools are blocked until an explicit approval flow exists.",
        )
