from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolCall:
    tool: str
    args: dict[str, Any] = field(default_factory=dict)
    reason: str = ""


@dataclass(frozen=True)
class Plan:
    goal: str
    steps: list[ToolCall]


@dataclass
class ToolResult:
    tool: str
    ok: bool
    data: Any
    error: str | None = None


@dataclass(frozen=True)
class RoleEvent:
    role: str
    message: str


@dataclass(frozen=True)
class ApprovalDecision:
    tool: str
    approved: bool
    risk: str
    reason: str
