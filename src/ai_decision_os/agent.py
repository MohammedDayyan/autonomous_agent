from __future__ import annotations

import asyncio
from functools import partial
from pathlib import Path
from typing import Any, Awaitable, Callable

from ai_decision_os.answer import AnswerAgent
from ai_decision_os.config import Settings
from ai_decision_os.llm import GroqClient
from ai_decision_os.mcp_client import MCPToolClient
from ai_decision_os.models import ApprovalDecision, RoleEvent, ToolCall, ToolResult
from ai_decision_os.policy import ApprovalPolicy
from ai_decision_os.planner import Planner
from ai_decision_os.scoring import score_observations
from ai_decision_os.strategies import choose_strategy
from ai_decision_os.tools.browser import extract_page
from ai_decision_os.tools.github import analyze_github_repo, list_user_repos
from ai_decision_os.tools.memory import MemoryStore
from ai_decision_os.tools.registry import ToolRegistry
from ai_decision_os.tools.report import render_research_report, save_report
from ai_decision_os.tools.search import search_web
from ai_decision_os.workspace import TaskWorkspace

EventCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


class DecisionAgent:
    def __init__(
        self,
        settings: Settings,
        tool_transport: str = "direct",
        max_iterations: int = 2,
        deep_extract_limit: int = 2,
    ) -> None:
        self.settings = settings
        self.tool_transport = tool_transport
        self.max_iterations = max_iterations
        self.deep_extract_limit = deep_extract_limit
        groq = (
            GroqClient(settings.groq_api_key, settings.groq_model)
            if settings.groq_api_key
            else None
        )
        self.planner = Planner(groq)
        self.answer_agent = AnswerAgent(groq)
        self.memory = MemoryStore(settings.memory_db)
        self.registry = self._build_registry(settings.reports_dir)
        self.policy = ApprovalPolicy()

    def _build_registry(self, reports_dir: Path) -> ToolRegistry:
        registry = ToolRegistry()
        registry.register("search_web", "Search the public web.", search_web)
        registry.register("extract_page", "Extract readable page text with Playwright.", extract_page)
        registry.register("analyze_github_repo", "Fetch GitHub repository metadata.", analyze_github_repo)
        registry.register("list_user_repos", "List public repositories for a GitHub user/organization.", list_user_repos)
        registry.register(
            "save_report",
            "Save a markdown report locally.",
            partial(save_report, reports_dir),
        )
        registry.register("save_memory", "Save task result to SQLite memory.", self.memory.save_memory)
        registry.register("search_memory", "Search previous task memory.", self.memory.search_memory)
        return registry

    async def run(self, goal: str, event_callback: EventCallback | None = None) -> dict[str, Any]:
        workspace = TaskWorkspace(self.settings.data_dir, goal)
        strategy = choose_strategy(goal)
        role_events: list[RoleEvent] = []
        approvals: list[ApprovalDecision] = []
        memory_context = await self.memory.search_memory(goal, limit=3)
        await self._emit(event_callback, "started", {"goal": goal, "strategy": strategy})

        role_events.append(RoleEvent("Memory Agent", f"Found {len(memory_context)} related memory records."))
        role_events.append(RoleEvent("Planner Agent", f"Selected strategy: {strategy}."))
        plan = await self.planner.create_plan(goal, memory_context=memory_context, strategy=strategy)
        observations: list[dict[str, Any]] = []
        results: list[ToolResult] = []
        executed_steps: list[ToolCall] = []

        if self.tool_transport == "mcp":
            async with MCPToolClient() as mcp_client:
                await self._run_loop(
                    goal, plan.steps, observations, results, executed_steps, approvals, mcp_client.call, event_callback
                )
        else:
            await self._run_loop(
                goal, plan.steps, observations, results, executed_steps, approvals, self.registry.call, event_callback
            )

        source_scores = score_observations(goal, observations)
        role_events.append(RoleEvent("Critic Agent", f"Scored {len(source_scores)} sources for confidence."))
        final_answer = await self.answer_agent.create_answer(goal, observations, source_scores)
        role_events.append(RoleEvent("Answer Agent", "Synthesized a concise final answer from research observations."))
        report_content = render_research_report(
            goal=goal,
            observations=observations,
            strategy=strategy,
            source_scores=source_scores,
            memory_context=memory_context,
            role_events=role_events,
            task_workspace=str(workspace.path),
        )

        report_step = ToolCall(
            "save_report",
            {"filename": self._report_name(goal), "content": report_content},
            "Write final report.",
        )
        if self.tool_transport == "mcp":
            async with MCPToolClient() as mcp_client:
                await self._execute_steps(
                    goal, [report_step], observations, results, executed_steps, approvals, mcp_client.call, event_callback
                )
                memory_step = ToolCall(
                    "save_memory",
                    {"task": goal, "result": self._memory_summary(goal, observations)},
                    "Persist run summary.",
                )
                await self._execute_steps(
                    goal, [memory_step], observations, results, executed_steps, approvals, mcp_client.call, event_callback
                )
        else:
            await self._execute_steps(
                goal, [report_step], observations, results, executed_steps, approvals, self.registry.call, event_callback
            )
            memory_step = ToolCall(
                "save_memory",
                {"task": goal, "result": self._memory_summary(goal, observations)},
                "Persist run summary.",
            )
            await self._execute_steps(
                goal, [memory_step], observations, results, executed_steps, approvals, self.registry.call, event_callback
            )

        workspace.write_json("plan.json", {"strategy": strategy, "steps": [step.__dict__ for step in executed_steps]})
        workspace.write_json("observations.json", observations)
        workspace.write_json("source_scores.json", source_scores)
        workspace.write_json("approvals.json", [approval.__dict__ for approval in approvals])
        workspace.write_json("roles.json", [event.__dict__ for event in role_events])
        workspace.write_text("report.md", report_content)
        await self._emit(event_callback, "finished", {"workspace": str(workspace.path)})

        # Close persistent Groq client sessions
        if self.planner.groq is not None:
            await self.planner.groq.close()
        if self.answer_agent.groq is not None:
            await self.answer_agent.groq.close()

        return {
            "goal": goal,
            "plan": {"goal": goal, "steps": executed_steps},
            "results": results,
            "observations": observations,
            "tool_transport": self.tool_transport,
            "strategy": strategy,
            "memory_context": memory_context,
            "source_scores": source_scores,
            "answer": final_answer,
            "approval_decisions": approvals,
            "role_events": role_events,
            "task_workspace": str(workspace.path),
        }

    async def _run_loop(
        self,
        goal: str,
        plan_steps: list[ToolCall],
        observations: list[dict[str, Any]],
        results: list[ToolResult],
        executed_steps: list[ToolCall],
        approvals: list[ApprovalDecision],
        call_tool: Any,
        event_callback: EventCallback | None,
    ) -> None:
        research_steps = [step for step in plan_steps if step.tool not in {"save_report", "save_memory"}]
        pending = research_steps
        extracted_urls: set[str] = set()

        for iteration in range(self.max_iterations):
            if not pending:
                break
            await self._emit(event_callback, "iteration", {"iteration": iteration + 1, "steps": len(pending)})
            await self._execute_steps(
                goal, pending, observations, results, executed_steps, approvals, call_tool, event_callback,
                concurrent=(iteration > 0)
            )
            pending = self._deep_research_steps(goal, observations, extracted_urls)

    async def _execute_step(
        self,
        step: Any,
        observations: list[dict[str, Any]],
        results: list[ToolResult],
        executed_steps: list[ToolCall],
        approvals: list[ApprovalDecision],
        call_tool: Any,
        event_callback: EventCallback | None,
    ) -> None:
        approval = self.policy.check(step.tool)
        approvals.append(approval)
        if not approval.approved:
            message = f"Blocked by approval policy: {approval.reason}"
            results.append(ToolResult(tool=step.tool, ok=False, data=None, error=message))
            observations.append({"tool": step.tool, "args": step.args, "data": {"error": message}})
            return

        args = dict(step.args)
        display_args = self._display_args(step.tool, args)
        executed_steps.append(ToolCall(step.tool, display_args, step.reason))
        await self._emit(event_callback, "tool_started", {"tool": step.tool, "args": args})

        try:
            data = await call_tool(step.tool, **args)
            results.append(ToolResult(tool=step.tool, ok=True, data=data))
            observations.append({"tool": step.tool, "args": display_args, "data": data})
            await self._emit(event_callback, "tool_finished", {"tool": step.tool, "ok": True})
        except Exception as exc:
            results.append(ToolResult(tool=step.tool, ok=False, data=None, error=str(exc)))
            observations.append(
                {"tool": step.tool, "args": display_args, "data": {"error": str(exc)}}
            )
            await self._emit(event_callback, "tool_finished", {"tool": step.tool, "ok": False, "error": str(exc)})

    async def _execute_steps(
        self,
        goal: str,
        steps: list[Any],
        observations: list[dict[str, Any]],
        results: list[ToolResult],
        executed_steps: list[ToolCall],
        approvals: list[ApprovalDecision],
        call_tool: Any,
        event_callback: EventCallback | None,
        concurrent: bool = False,
    ) -> None:
        if concurrent and len(steps) > 1:
            tasks = [
                self._execute_step(step, observations, results, executed_steps, approvals, call_tool, event_callback)
                for step in steps
            ]
            await asyncio.gather(*tasks)
        else:
            for step in steps:
                await self._execute_step(step, observations, results, executed_steps, approvals, call_tool, event_callback)

    def _display_args(self, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        display_args = dict(args)
        if tool == "save_report" and isinstance(display_args.get("content"), str):
            display_args["content"] = f"<{len(display_args['content'])} chars>"
        if tool == "save_memory" and isinstance(display_args.get("result"), str):
            display_args["result"] = display_args["result"][:240]
        return display_args

    def _deep_research_steps(
        self,
        goal: str,
        observations: list[dict[str, Any]],
        extracted_urls: set[str],
    ) -> list[ToolCall]:
        steps: list[ToolCall] = []
        scored = score_observations(goal, observations)
        for source in scored:
            if len(steps) >= self.deep_extract_limit:
                break
            url = str(source.get("url") or "")
            if not url.startswith(("http://", "https://")):
                continue
            if any(blocked in url for blocked in ["duckduckgo.com", "tavily.com"]):
                continue
            if url in extracted_urls:
                continue
            extracted_urls.add(url)
            steps.append(ToolCall("extract_page", {"url": url, "max_chars": 4000}, "Deep-read a high-confidence source."))
        return steps

    async def _emit(self, callback: EventCallback | None, event: str, payload: dict[str, Any]) -> None:
        if callback is None:
            return
        maybe = callback({"event": event, **payload})
        if maybe is not None:
            await maybe

    def _report_name(self, goal: str) -> str:
        from ai_decision_os.tools.report import safe_filename

        return f"{safe_filename(goal)}.md"

    def _memory_summary(self, goal: str, observations: list[dict[str, Any]]) -> str:
        report_paths: list[str] = []
        for item in observations:
            if item.get("tool") != "save_report" or not isinstance(item.get("data"), dict):
                continue
            path = item["data"].get("path")
            if isinstance(path, str):
                report_paths.append(path)
        return f"Goal: {goal}\nTools run: {len(observations)}\nReports: {', '.join(report_paths)}"
