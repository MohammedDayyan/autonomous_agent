# AI Decision OS

An MCP-powered **Reason -> Research -> Execute** agent.

The project demonstrates a modern agent architecture:

- Groq-hosted model planning
- MCP tool exposure
- MCP client execution mode
- Web and GitHub research tools
- Tavily search integration
- Playwright browser extraction
- Iterative Plan -> Act -> Observe -> Re-plan research loop
- Source confidence scoring
- Strategy selection for comparisons, GitHub research, jobs, docs, and market tasks
- Task workspaces with plan, observations, approvals, sources, and report artifacts
- Human-approval policy primitives for risky future tools
- Multi-role trace: Memory, Planner, Critic, and Report behavior
- Streaming web UI progress events
- SQLite memory
- Markdown report generation
- A runnable CLI with an offline fallback planner

## Resume-Ready Feature Set

AI Decision OS is designed as a small production-style agent runtime, not a plain chatbot:

- **MCP client/server architecture:** exposes local tools through an MCP server and can call those tools through MCP stdio.
- **Planner -> tool execution loop:** converts a user goal into concrete tool calls, executes them, observes results, and performs follow-up extraction.
- **Streaming web UI:** shows live run state, current tool activity, success counts, report previews, and downloadable reports.
- **Research tooling:** combines web search, page extraction, GitHub repository analysis, source scoring, and report generation.
- **Local memory:** saves and searches prior task summaries in SQLite.
- **Traceability:** stores plan, observations, approvals, role events, source scores, reports, and task workspaces.
- **Safety primitives:** includes an approval-policy layer for gating future risky tools.
- **Fallback behavior:** can run with heuristic planning when no model key is configured.

Good interview summary:

```text
Built an MCP-powered AI research agent with planning, MCP tool execution,
streaming progress UI, SQLite memory, source confidence scoring, task traces,
and downloadable Markdown reports.
```

## Benchmark-Style Evaluation

The project includes a local benchmark harness inspired by established agent benchmarks. These runs are not official leaderboard submissions; they are practical regression tests that measure task success, tool success rate, and latency.

| Benchmark family | What it tests in this project |
| --- | --- |
| MCP-AgentBench style | MCP-mediated tool orchestration across search, report, and memory tools. |
| GAIA style | Open-ended research, synthesis, and artifact generation. |
| WebArena style | Web search followed by page extraction and grounded reporting. |
| BFCL / ToolBench style | Correct tool selection for multi-step comparison workflows. |
| SWE-bench inspired | Repository-focused analysis using GitHub tooling. |

Run the benchmark suite:

```powershell
.\.venv\Scripts\python.exe -m ai_decision_os.benchmark --tool-transport mcp
```

Run a shorter smoke benchmark:

```powershell
.\.venv\Scripts\python.exe -m ai_decision_os.benchmark --tool-transport mcp --limit 1
```

The benchmark report is saved by default to:

```text
.decision_os/benchmarks/latest.md
```

## Quick Start

```powershell
.\.venv\Scripts\python.exe -m pip install -e .[dev]
Copy-Item .env.example .env
```

Add your Groq and Tavily keys to `.env`:

```text
GROQ_API_KEY=gsk_...
TAVILY_API_KEY=tvly-...
```

Tavily is optional, but recommended. Without it, search falls back to a lightweight DuckDuckGo path.

Run a task:

```powershell
.\.venv\Scripts\decision-os "Find top open-source AI agents on GitHub and save a report"
```

Run the agent through its MCP server instead of direct in-process tool calls:

```powershell
.\.venv\Scripts\decision-os --tool-transport mcp "Find top open-source AI agents on GitHub"
```

Or without installing the console script:

```powershell
.\.venv\Scripts\python.exe -m ai_decision_os.cli "Research Python AI frameworks"
```

## MCP Server

Expose the tools to an MCP client:

```powershell
.\.venv\Scripts\decision-os-mcp
```

## Web UI

Start the interactive website:

```powershell
.\.venv\Scripts\python.exe -m ai_decision_os.web
```

Then open:

```text
http://127.0.0.1:8000
```

The web UI streams progress while the agent runs:

```text
Planning -> tool started -> tool finished -> deep extraction -> report saved
```

Available MCP tools:

- `search_web`
- `extract_page`
- `analyze_github_repo`
- `save_report`
- `save_memory`
- `search_memory`

## MCP Client Usage

This repo now has both sides:

```text
CLI / DecisionAgent
  |
  v
MCPToolClient
  |
  v
ai_decision_os.mcp_server over stdio
  |
  v
MCP tools
```

Use `--tool-transport mcp` to make the local agent act as the MCP client.

External MCP clients can also use the server. Example server command:

```json
{
  "mcpServers": {
    "ai-decision-os": {
      "command": "C:\\Users\\DELL\\Downloads\\MCP_USING\\.venv\\Scripts\\python.exe",
      "args": ["-m", "ai_decision_os.mcp_server"],
      "cwd": "C:\\Users\\DELL\\Downloads\\MCP_USING"
    }
  }
}
```

## Architecture

```text
User Goal
  |
  v
Planner (Groq JSON plan, fallback heuristic plan)
  |
  v
Agent Runtime
  |
  v
Tool Registry
  |-- Search Tool
  |-- Browser Tool
  |-- GitHub Tool
  |-- Report Tool
  |-- SQLite Memory Tool
```

## Example

```powershell
.\.venv\Scripts\python.exe -m ai_decision_os.cli "Find top open-source AI agents on GitHub"
```

The agent will:

1. create a plan,
2. search memory for prior related work,
3. choose a research strategy,
4. run research tools,
5. deep-read high-confidence sources,
6. score evidence,
7. generate a markdown report,
8. save the result under `.decision_os/reports`,
9. persist task memory in `.decision_os/memory.sqlite3`,
10. save full run artifacts under `.decision_os/tasks`.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```
