from __future__ import annotations

import argparse
import asyncio
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ai_decision_os.agent import DecisionAgent
from ai_decision_os.config import load_settings


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    benchmark_family: str
    goal: str
    required_tools: tuple[str, ...]
    description: str


@dataclass(frozen=True)
class BenchmarkResult:
    name: str
    benchmark_family: str
    passed: bool
    latency_seconds: float
    tool_success_rate: float
    required_tools_used: list[str]
    missing_tools: list[str]
    report_saved: bool
    task_workspace: str


DEFAULT_CASES: tuple[BenchmarkCase, ...] = (
    BenchmarkCase(
        name="mcp_protocol_research",
        benchmark_family="MCP-AgentBench style",
        goal="How can Model Context Protocol be used? Save a concise report.",
        required_tools=("search_web", "save_report", "save_memory"),
        description="Tests MCP-mediated tool orchestration, report writing, and memory persistence.",
    ),
    BenchmarkCase(
        name="general_research_gaia",
        benchmark_family="GAIA style",
        goal="Research what OSINT is, include practical use cases, and save a report.",
        required_tools=("search_web", "save_report"),
        description="Tests open-ended research, synthesis, and artifact generation.",
    ),
    BenchmarkCase(
        name="web_extraction_webarena",
        benchmark_family="WebArena style",
        goal="Research Model Context Protocol documentation and deep-read the best official source.",
        required_tools=("search_web", "extract_page", "save_report"),
        description="Tests web search followed by page extraction and grounded reporting.",
    ),
    BenchmarkCase(
        name="tool_selection_bfcl",
        benchmark_family="BFCL / ToolBench style",
        goal="Compare CrewAI, AutoGen, and LangGraph for backend automation and save a report.",
        required_tools=("search_web", "save_report", "save_memory"),
        description="Tests function/tool selection for a comparison workflow.",
    ),
    BenchmarkCase(
        name="github_analysis_swebench_inspired",
        benchmark_family="SWE-bench inspired",
        goal="Analyze the GitHub repository langchain-ai/langgraph and save a report.",
        required_tools=("analyze_github_repo", "save_report"),
        description="Tests repository-focused analysis, similar in spirit to coding-agent benchmark tasks.",
    ),
)


async def run_benchmark_case(case: BenchmarkCase, tool_transport: str) -> BenchmarkResult:
    settings = load_settings()
    agent = DecisionAgent(settings, tool_transport=tool_transport)
    started = time.perf_counter()
    output = await agent.run(case.goal)
    latency = time.perf_counter() - started

    results = output.get("results", [])
    used_tools = [result.tool for result in results]
    successful_tools = [result.tool for result in results if result.ok]
    missing_tools = [tool for tool in case.required_tools if tool not in successful_tools]
    report_saved = any(result.tool == "save_report" and result.ok for result in results)
    tool_success_rate = len(successful_tools) / len(results) if results else 0.0

    return BenchmarkResult(
        name=case.name,
        benchmark_family=case.benchmark_family,
        passed=not missing_tools and report_saved,
        latency_seconds=round(latency, 2),
        tool_success_rate=round(tool_success_rate, 3),
        required_tools_used=[tool for tool in case.required_tools if tool in used_tools],
        missing_tools=missing_tools,
        report_saved=report_saved,
        task_workspace=str(output.get("task_workspace", "")),
    )


def summarize_results(results: list[BenchmarkResult]) -> dict[str, Any]:
    passed = sum(1 for result in results if result.passed)
    avg_latency = sum(result.latency_seconds for result in results) / len(results) if results else 0.0
    avg_tool_success = sum(result.tool_success_rate for result in results) / len(results) if results else 0.0
    return {
        "cases": len(results),
        "passed": passed,
        "pass_rate": round(passed / len(results), 3) if results else 0.0,
        "avg_latency_seconds": round(avg_latency, 2),
        "avg_tool_success_rate": round(avg_tool_success, 3),
    }


def write_benchmark_report(path: Path, results: list[BenchmarkResult]) -> None:
    summary = summarize_results(results)
    lines = [
        "# AI Decision OS Benchmark Report",
        "",
        "These are local benchmark-style evaluations inspired by established agent benchmarks.",
        "They are not official leaderboard scores.",
        "",
        "## Summary",
        "",
        f"- Cases: {summary['cases']}",
        f"- Passed: {summary['passed']}",
        f"- Pass rate: {summary['pass_rate']}",
        f"- Average latency seconds: {summary['avg_latency_seconds']}",
        f"- Average tool success rate: {summary['avg_tool_success_rate']}",
        "",
        "## Results",
        "",
        "| Case | Benchmark family | Passed | Tool success | Latency | Missing tools |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]
    for result in results:
        missing = ", ".join(result.missing_tools) if result.missing_tools else "-"
        lines.append(
            f"| {result.name} | {result.benchmark_family} | {result.passed} | "
            f"{result.tool_success_rate} | {result.latency_seconds}s | {missing} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def run_benchmarks(tool_transport: str, limit: int | None, output: Path | None) -> int:
    cases = list(DEFAULT_CASES[:limit] if limit else DEFAULT_CASES)
    results: list[BenchmarkResult] = []
    for case in cases:
        print(f"Running {case.name} ({case.benchmark_family})...")
        results.append(await run_benchmark_case(case, tool_transport))

    summary = summarize_results(results)
    print(json.dumps({"summary": summary, "results": [asdict(result) for result in results]}, indent=2))

    if output is not None:
        write_benchmark_report(output, results)
        print(f"\nBenchmark report saved: {output}")

    return 0 if all(result.passed for result in results) else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local benchmark-style evaluations for AI Decision OS.")
    parser.add_argument("--tool-transport", choices=["direct", "mcp"], default="mcp")
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N benchmark cases.")
    parser.add_argument("--output", type=Path, default=Path(".decision_os/benchmarks/latest.md"))
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run_benchmarks(args.tool_transport, args.limit, args.output)))


if __name__ == "__main__":
    main()
