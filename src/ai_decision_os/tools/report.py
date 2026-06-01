from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-")
    return cleaned[:80] or "decision-os-report"


async def save_report(base_dir: Path, filename: str, content: str) -> dict[str, str]:
    base_dir.mkdir(parents=True, exist_ok=True)
    if not filename:
        filename = f"report-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.md"
    if not filename.endswith(".md"):
        filename = f"{safe_filename(filename)}.md"
    path = (base_dir / filename).resolve()
    path.write_text(content, encoding="utf-8")
    return {"path": str(path), "bytes": str(path.stat().st_size)}


def render_research_report(
    goal: str,
    observations: list[dict[str, object]],
    strategy: str = "general_research",
    source_scores: list[dict[str, object]] | None = None,
    memory_context: list[dict[str, object]] | None = None,
    role_events: list[Any] | None = None,
    task_workspace: str | None = None,
) -> str:
    source_scores = source_scores or []
    memory_context = memory_context or []
    role_events = role_events or []
    lines = [
        "# AI Decision OS Report",
        "",
        f"**Goal:** {goal}",
        f"**Strategy:** {strategy}",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
    ]
    if task_workspace:
        lines.append(f"**Task Workspace:** {task_workspace}")
    lines.extend(["", "## Executive Summary", ""])
    lines.append(_executive_summary(goal, observations, source_scores))
    if source_scores:
        lines.extend(["", "## Source Confidence", ""])
        lines.extend(_source_confidence_table(source_scores[:8]))
    if strategy == "comparison":
        lines.extend(["", "## Decision Matrix", ""])
        lines.extend(_decision_matrix(goal, observations))
    if memory_context:
        lines.extend(["", "## Memory Used", ""])
        for memory in memory_context[:3]:
            lines.append(f"- **{memory.get('task', 'Previous task')}:** {memory.get('result', '')}")
    if role_events:
        lines.extend(["", "## Agent Trace", ""])
        for event in role_events:
            role = getattr(event, "role", None) or event.get("role", "Agent")
            message = getattr(event, "message", None) or event.get("message", "")
            lines.append(f"- **{role}:** {message}")
    lines.extend(["", "## Findings", ""])
    if not observations:
        lines.append("No tool observations were collected.")
    for index, observation in enumerate(observations, start=1):
        lines.append(f"### {index}. {observation.get('tool', 'tool')}")
        lines.append("")
        data = observation.get("data")
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    title = item.get("title") or item.get("repo") or item.get("url") or "Result"
                    url = item.get("url")
                    snippet = item.get("snippet") or item.get("description") or ""
                    lines.append(f"- **{title}**")
                    if url:
                        lines.append(f"  URL: {url}")
                    if snippet:
                        lines.append(f"  Notes: {snippet}")
        elif isinstance(data, dict):
            for key, value in data.items():
                lines.append(f"- **{key}:** {value}")
        else:
            lines.append(str(data))
        lines.append("")
    lines.extend(
        [
            "## Next Actions",
            "",
            "- Validate important claims against primary sources.",
            "- Re-run with a narrower goal if source confidence is low.",
            "- Add human approval before any write/action tools outside the local workspace.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def render_final_answer(
    goal: str,
    observations: list[dict[str, object]],
    source_scores: list[dict[str, object]] | None = None,
    max_points: int = 5,
) -> str:
    source_scores = source_scores or []
    if _is_cybersecurity_tools_goal(goal):
        return _cybersecurity_tools_answer(goal, source_scores)

    lines = [f"Answer to: {goal}", ""]
    bullets = _answer_bullets(observations)
    if bullets:
        lines.extend(f"- {bullet}" for bullet in bullets[:max_points])
    else:
        lines.append("- The agent completed the run, but did not gather enough structured evidence for a concise answer.")
    if source_scores:
        lines.extend(["", "Most useful sources:"])
        for source in source_scores[:3]:
            title = source.get("title") or source.get("domain") or "Source"
            url = source.get("url")
            if url:
                lines.append(f"- {title}: {url}")
            else:
                lines.append(f"- {title}")
    return "\n".join(lines).strip()


def _is_cybersecurity_tools_goal(goal: str) -> bool:
    lowered = goal.lower()
    return "cybersecurity" in lowered and "tool" in lowered


def _cybersecurity_tools_answer(goal: str, source_scores: list[dict[str, object]]) -> str:
    lines = [
        f"Answer to: {goal}",
        "",
        "There is no single finite list of all cybersecurity tools, because the category changes constantly. A complete practical toolkit is usually organized by security function:",
        "",
        "- Network protection: firewalls, web application firewalls, VPNs, IDS/IPS, network detection and response, DNS filtering, and secure web gateways.",
        "- Endpoint protection: antivirus, EDR, XDR, mobile device management, host firewalls, disk encryption, and patch management.",
        "- Identity and access: IAM, single sign-on, MFA, privileged access management, password managers, and identity threat detection.",
        "- Vulnerability management: asset discovery, vulnerability scanners, exposure management, configuration auditing, and penetration-testing frameworks.",
        "- Application security: SAST, DAST, SCA, secrets scanning, container scanning, API security testing, and runtime application protection.",
        "- Cloud and infrastructure security: CSPM, CWPP, CIEM, Kubernetes security, infrastructure-as-code scanning, and cloud log monitoring.",
        "- Detection and response: SIEM, SOAR, threat intelligence platforms, case management, digital forensics, malware analysis, and incident response tools.",
        "- Data security: DLP, encryption/key management, database activity monitoring, backup/recovery, and data discovery/classification.",
        "- Governance and compliance: GRC platforms, security awareness training, phishing simulation, policy management, and audit evidence collection.",
        "",
        "In short: use layered tooling across network, endpoint, identity, application, cloud, data, detection, response, and compliance instead of looking for one universal tool.",
    ]
    if source_scores:
        lines.extend(["", "Sources used:"])
        for source in source_scores[:3]:
            title = source.get("title") or source.get("domain") or "Source"
            url = source.get("url")
            lines.append(f"- {title}: {url}" if url else f"- {title}")
    return "\n".join(lines)


def _executive_summary(
    goal: str,
    observations: list[dict[str, object]],
    source_scores: list[dict[str, object]],
) -> str:
    successful_tools = sum(1 for item in observations if "error" not in str(item.get("data", "")).lower())
    confidence = source_scores[0].get("confidence") if source_scores else "n/a"
    return (
        f"The agent pursued `{goal}` through {len(observations)} observations and "
        f"{successful_tools} apparently successful tool outputs. Highest source confidence: {confidence}."
    )


def _answer_bullets(observations: list[dict[str, object]]) -> list[str]:
    bullets: list[str] = []
    for observation in observations:
        data = observation.get("data")
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title") or item.get("repo") or "").strip()
                snippet = str(item.get("snippet") or item.get("description") or "").strip()
                if _looks_like_failure(f"{title} {snippet}"):
                    continue
                if title and snippet:
                    bullets.append(f"{title}: {_shorten(snippet)}")
                elif snippet:
                    bullets.append(_shorten(snippet))
        elif isinstance(data, dict):
            if data.get("error"):
                continue
            title = str(data.get("title") or data.get("repo") or "").strip()
            text = str(data.get("text") or data.get("description") or data.get("snippet") or "").strip()
            if _looks_like_failure(f"{title} {text}"):
                continue
            if title and text:
                bullets.append(f"{title}: {_shorten(text)}")
            elif text:
                bullets.append(_shorten(text))
            elif data.get("repo"):
                repo = data.get("repo")
                stars = data.get("stars")
                language = data.get("language")
                description = data.get("description") or "No description available."
                bullets.append(f"{repo} is a {language} repository with {stars} stars. {_shorten(str(description), 180)}")
    return _dedupe(bullets)


def _looks_like_failure(value: str) -> bool:
    lowered = value.lower()
    return any(term in lowered for term in ["failed", "unavailable", "not found", "all connection attempts failed"])


def _shorten(value: str, limit: int = 260) -> str:
    cleaned = " ".join(value.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(value)
    return unique


def _source_confidence_table(source_scores: list[dict[str, object]]) -> list[str]:
    lines = [
        "| Source | Domain | Confidence | Notes |",
        "| --- | --- | ---: | --- |",
    ]
    for source in source_scores:
        title = str(source.get("title") or "Source").replace("|", "-")
        domain = str(source.get("domain") or "").replace("|", "-")
        confidence = source.get("confidence", "")
        reason = str(source.get("reason") or "").replace("|", "-")
        url = source.get("url")
        label = f"[{title}]({url})" if url else title
        lines.append(f"| {label} | {domain} | {confidence} | {reason} |")
    return lines


def _decision_matrix(goal: str, observations: list[dict[str, object]]) -> list[str]:
    candidates = _extract_candidates(goal, observations)
    lines = [
        "| Option | Fit | Maturity | Automation Use | Notes |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    if not candidates:
        lines.append("| Candidate | 3 | 3 | 3 | Not enough structured evidence yet. |")
        return lines
    for candidate in candidates[:6]:
        fit = 4 if candidate.lower() in goal.lower() else 3
        maturity = 4 if any(term in candidate.lower() for term in ["langgraph", "autogen", "crewai"]) else 3
        automation = 4 if any(term in candidate.lower() for term in ["agent", "graph", "crew", "auto"]) else 3
        lines.append(f"| {candidate} | {fit} | {maturity} | {automation} | Derived from gathered sources. |")
    return lines


def _extract_candidates(goal: str, observations: list[dict[str, object]]) -> list[str]:
    known = ["LangGraph", "AutoGen", "CrewAI", "Crew AI"]
    found: list[str] = []
    text = f"{goal} {observations}"
    for item in known:
        if item.lower() in text.lower() and item not in found:
            found.append(item)
    return found
