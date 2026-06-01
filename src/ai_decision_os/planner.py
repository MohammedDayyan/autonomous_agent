from __future__ import annotations

from ai_decision_os.llm import GroqClient
from ai_decision_os.models import Plan, ToolCall
from ai_decision_os.strategies import strategy_queries


PLANNER_SYSTEM_PROMPT = """You are the planner for AI Decision OS.
Return strict JSON with this schema:
{
  "steps": [
    {"tool": "search_web|extract_page|analyze_github_repo|list_user_repos|save_report|save_memory|search_memory", "args": {}, "reason": ""}
  ]
}

Rules:
- Prefer search_web for broad research.
- Use analyze_github_repo only for explicit owner/repo values.
- End useful research tasks with save_report and save_memory.
- Do not use placeholders such as {result_of_step_1}; every argument must be concrete.
- Keep plans short: 3 to 6 steps.
"""


class Planner:
    def __init__(self, groq: GroqClient | None = None) -> None:
        self.groq = groq

    async def create_plan(
        self,
        goal: str,
        memory_context: list[dict[str, object]] | None = None,
        strategy: str = "general_research",
    ) -> Plan:
        if self.groq is None:
            return self._fallback_plan(goal, strategy)

        try:
            memory_note = ""
            if memory_context:
                memory_note = f"\nRelevant memory:\n{memory_context[:3]}"
            payload = await self.groq.complete_json(
                PLANNER_SYSTEM_PROMPT,
                f"Goal: {goal}\nStrategy: {strategy}{memory_note}",
            )
            steps = [
                ToolCall(
                    tool=str(step["tool"]),
                    args=dict(step.get("args", {})),
                    reason=str(step.get("reason", "")),
                )
                for step in payload.get("steps", [])
            ]
            steps = self._sanitize_steps(goal, steps)
            if steps:
                return Plan(goal=goal, steps=steps)
        except Exception:
            return self._fallback_plan(goal, strategy)

        return self._fallback_plan(goal, strategy)

    def _fallback_plan(self, goal: str, strategy: str = "general_research") -> Plan:
        normalized = goal.lower()
        steps: list[ToolCall] = []

        queries = strategy_queries(goal, strategy)
        for query in queries[:3]:
            steps.append(
                ToolCall("search_web", {"query": query}, f"Research using the {strategy} strategy.")
            )

        if "github" in normalized and all("site:github.com" not in step.args["query"] for step in steps):
            steps.append(ToolCall("search_web", {"query": f"{goal} site:github.com"}, "Find GitHub projects."))

        steps.extend(
            [
                ToolCall(
                    "save_report",
                    {"filename": "", "content": ""},
                    "Create a markdown research report from gathered evidence.",
                ),
                ToolCall(
                    "save_memory",
                    {"task": goal, "result": ""},
                    "Persist the outcome for future retrieval.",
                ),
            ]
        )
        return Plan(goal=goal, steps=steps)

    def _sanitize_steps(self, goal: str, steps: list[ToolCall]) -> list[ToolCall]:
        sanitized: list[ToolCall] = []
        has_search = False

        for step in steps:
            args = dict(step.args)
            if any(isinstance(value, str) and "{" in value for value in args.values()):
                if step.tool not in {"save_report", "save_memory"}:
                    continue

            if step.tool == "search_web":
                query = str(args.get("query") or goal)
                sanitized.append(ToolCall("search_web", {"query": query}, step.reason))
                has_search = True
            elif step.tool == "extract_page":
                url = args.get("url")
                if isinstance(url, str) and url.startswith(("http://", "https://")):
                    sanitized.append(ToolCall("extract_page", {"url": url}, step.reason))
            elif step.tool == "analyze_github_repo":
                repo = args.get("repo")
                owner = args.get("owner")
                if owner and repo:
                    repo = f"{owner}/{repo}"
                if isinstance(repo, str) and "/" in repo and "{" not in repo:
                    sanitized.append(ToolCall("analyze_github_repo", {"repo": repo}, step.reason))
            elif step.tool == "list_user_repos":
                username = args.get("username") or args.get("owner") or args.get("user") or goal
                if isinstance(username, str) and "{" not in username:
                    sanitized.append(ToolCall("list_user_repos", {"username": username}, step.reason))
            elif step.tool == "save_report":
                filename = str(args.get("filename") or "")
                content = str(args.get("content") or "")
                if "{" in content:
                    content = ""
                sanitized.append(ToolCall("save_report", {"filename": filename, "content": content}, step.reason))
            elif step.tool == "save_memory":
                task = str(args.get("task") or args.get("key") or goal)
                result = str(args.get("result") or args.get("value") or "")
                if "{" in result:
                    result = ""
                sanitized.append(ToolCall("save_memory", {"task": task, "result": result}, step.reason))
            elif step.tool == "search_memory":
                query = str(args.get("query") or goal)
                sanitized.append(ToolCall("search_memory", {"query": query}, step.reason))

        if not has_search:
            sanitized.insert(0, ToolCall("search_web", {"query": goal}, "Collect research material."))
        if not any(step.tool == "save_report" for step in sanitized):
            sanitized.append(ToolCall("save_report", {"filename": "", "content": ""}, "Save a report."))
        if not any(step.tool == "save_memory" for step in sanitized):
            sanitized.append(ToolCall("save_memory", {"task": goal, "result": ""}, "Persist the result."))

        return sanitized[:6]
