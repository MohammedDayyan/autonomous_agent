from __future__ import annotations

import asyncio
import json
import os
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.responses import FileResponse, JSONResponse, StreamingResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from ai_decision_os.agent import DecisionAgent
from ai_decision_os.config import load_settings

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "web_static"


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [to_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


async def homepage(_request) -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


async def run_agent(request) -> JSONResponse:
    payload = await request.json()
    goal = str(payload.get("goal", "")).strip()
    transport = str(payload.get("transport", "direct")).strip()

    if not goal:
        return JSONResponse({"error": "Goal is required."}, status_code=400)
    if transport not in {"direct", "mcp"}:
        return JSONResponse({"error": "Transport must be direct or mcp."}, status_code=400)

    agent = DecisionAgent(load_settings(), tool_transport=transport)
    output = await agent.run(goal)
    return JSONResponse(to_jsonable(output))


async def stream_agent(request) -> StreamingResponse:
    goal = str(request.query_params.get("goal", "")).strip()
    transport = str(request.query_params.get("transport", "direct")).strip()

    if not goal or transport not in {"direct", "mcp"}:
        async def error_stream():
            yield _sse({"event": "error", "error": "Goal and valid transport are required."})

        return StreamingResponse(error_stream(), media_type="text/event-stream")

    async def event_stream():
        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

        async def publish(event: dict[str, Any]) -> None:
            await queue.put(to_jsonable(event))

        async def run() -> None:
            try:
                agent = DecisionAgent(load_settings(), tool_transport=transport)
                output = await agent.run(goal, event_callback=publish)
                await queue.put({"event": "complete", "output": to_jsonable(output)})
            except Exception as exc:
                await queue.put({"event": "error", "error": str(exc)})
            finally:
                await queue.put(None)

        task = asyncio.create_task(run())
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=10)
                except TimeoutError:
                    yield _sse({"event": "heartbeat"})
                    continue
                if event is None:
                    break
                yield _sse(event)
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


async def list_reports(_request) -> JSONResponse:
    settings = load_settings()
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    reports = [
        {
            "name": path.name,
            "path": str(path),
            "size": path.stat().st_size,
            "modified": path.stat().st_mtime,
        }
        for path in sorted(settings.reports_dir.glob("*.md"), key=lambda item: item.stat().st_mtime, reverse=True)
    ]
    return JSONResponse({"reports": reports})


async def read_report(request) -> JSONResponse:
    settings = load_settings()
    name = request.path_params["name"]
    path = _report_path(settings.reports_dir, name)
    if path is None:
        return JSONResponse({"error": "Report not found."}, status_code=404)
    return JSONResponse({"name": path.name, "content": path.read_text(encoding="utf-8")})


async def download_report(request) -> FileResponse | JSONResponse:
    settings = load_settings()
    name = request.path_params["name"]
    path = _report_path(settings.reports_dir, name)
    if path is None:
        return JSONResponse({"error": "Report not found."}, status_code=404)
    return FileResponse(path, media_type="text/markdown", filename=path.name)


def _report_path(reports_dir: Path, name: str) -> Path | None:
    path = (reports_dir / name).resolve()
    resolved_reports_dir = reports_dir.resolve()
    if resolved_reports_dir not in path.parents or not path.exists() or path.suffix != ".md":
        return None
    return path


app = Starlette(
    debug=False,
    routes=[
        Route("/", homepage),
        Route("/api/run", run_agent, methods=["POST"]),
        Route("/api/run-stream", stream_agent),
        Route("/api/reports", list_reports),
        Route("/api/reports/{name}/download", download_report),
        Route("/api/reports/{name}", read_report),
        Mount("/static", StaticFiles(directory=STATIC_DIR), name="static"),
    ],
)


def main() -> None:
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("ai_decision_os.web:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
