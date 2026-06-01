from __future__ import annotations

import asyncio

from ai_decision_os.planner import Planner


def test_fallback_planner_creates_research_report_and_memory_steps() -> None:
    plan = asyncio.run(Planner().create_plan("Find top open-source AI agents on GitHub"))

    assert plan.steps[0].tool == "search_web"
    assert any("site:github.com" in step.args["query"] for step in plan.steps if step.tool == "search_web")
    assert [step.tool for step in plan.steps][-2:] == ["save_report", "save_memory"]


def test_planner_sanitizes_placeholder_tool_arguments() -> None:
    steps = Planner()._sanitize_steps(
        "Find top open-source AI agents on GitHub",
        [
            type("Step", (), {
                "tool": "extract_page",
                "args": {"url": "{result_of_step_1}", "selector": "repositories"},
                "reason": "placeholder",
            })(),
            type("Step", (), {
                "tool": "save_memory",
                "args": {"key": "top_ai_agents", "value": "{result_of_step_3}"},
                "reason": "alias args",
            })(),
        ],
    )

    assert [step.tool for step in steps] == ["search_web", "save_memory", "save_report"]
    assert steps[1].args == {"task": "top_ai_agents", "result": ""}
