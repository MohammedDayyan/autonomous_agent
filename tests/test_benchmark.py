from __future__ import annotations

from ai_decision_os.benchmark import BenchmarkResult, summarize_results


def test_benchmark_summary_calculates_rates() -> None:
    results = [
        BenchmarkResult(
            name="one",
            benchmark_family="GAIA style",
            passed=True,
            latency_seconds=2.0,
            tool_success_rate=1.0,
            required_tools_used=["search_web"],
            missing_tools=[],
            report_saved=True,
            task_workspace="workspace-one",
        ),
        BenchmarkResult(
            name="two",
            benchmark_family="MCP-AgentBench style",
            passed=False,
            latency_seconds=4.0,
            tool_success_rate=0.5,
            required_tools_used=["search_web"],
            missing_tools=["save_report"],
            report_saved=False,
            task_workspace="workspace-two",
        ),
    ]

    summary = summarize_results(results)

    assert summary == {
        "cases": 2,
        "passed": 1,
        "pass_rate": 0.5,
        "avg_latency_seconds": 3.0,
        "avg_tool_success_rate": 0.75,
    }
