from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_decision_os.tools.report import safe_filename


class TaskWorkspace:
    def __init__(self, data_dir: Path, goal: str) -> None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        self.path = data_dir / "tasks" / f"{stamp}-{safe_filename(goal)}"
        self.path.mkdir(parents=True, exist_ok=True)

    def write_json(self, name: str, data: Any) -> Path:
        path = self.path / name
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        return path

    def write_text(self, name: str, content: str) -> Path:
        path = self.path / name
        path.write_text(content, encoding="utf-8")
        return path
