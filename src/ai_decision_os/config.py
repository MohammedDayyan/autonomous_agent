from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    groq_api_key: str | None
    groq_model: str
    data_dir: Path

    @property
    def reports_dir(self) -> Path:
        return self.data_dir / "reports"

    @property
    def memory_db(self) -> Path:
        return self.data_dir / "memory.sqlite3"


def load_settings() -> Settings:
    load_dotenv()
    data_dir = Path(os.getenv("DECISION_OS_DATA_DIR", ".decision_os")).resolve()
    return Settings(
        groq_api_key=os.getenv("GROQ_API_KEY") or None,
        groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        data_dir=data_dir,
    )
