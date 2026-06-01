from __future__ import annotations

import argparse
import asyncio

from ai_decision_os.agent import DecisionAgent
from ai_decision_os.config import load_settings


async def run_cli(goal: str, tool_transport: str) -> int:
    agent = DecisionAgent(load_settings(), tool_transport=tool_transport)
    output = await agent.run(goal)

    print(f"Goal: {output['goal']}")
    print(f"Tool transport: {output['tool_transport']}")
    print(f"Strategy: {output.get('strategy', 'n/a')}")
    print(f"Task workspace: {output.get('task_workspace', 'n/a')}")
    print("\nPlan:")
    for index, step in enumerate(output["plan"]["steps"], start=1):
        print(f"{index}. {step.tool} {step.args} - {step.reason}")

    print("\nResults:")
    for result in output["results"]:
        status = "ok" if result.ok else "error"
        print(f"- {result.tool}: {status}")
        if result.tool == "save_report" and result.ok:
            print(f"  saved: {result.data['path']}")
        elif result.error:
            print(f"  {result.error}")

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AI Decision OS agent.")
    parser.add_argument("goal", help="The goal the agent should research and execute.")
    parser.add_argument(
        "--tool-transport",
        choices=["direct", "mcp"],
        default="direct",
        help="Use direct Python calls or MCP stdio calls to execute tools.",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run_cli(args.goal, args.tool_transport)))


if __name__ == "__main__":
    main()
