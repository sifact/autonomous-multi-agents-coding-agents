"""Shared formatting of state into prompt text, plus the event record every node emits."""
from __future__ import annotations

from typing import Any

from coding_agent.agents.prompts import MAX_EXEC_PROMPT_CHARS, MAX_FILES_PROMPT_CHARS
from coding_agent.graph import Step
from coding_agent.llm import Usage
from coding_agent.sandbox import ExecResult, truncate


def format_plan(steps: list[Step]) -> str:
    return "\n".join(f"{s.id}. {s.description} (done when: {s.acceptance})" for s in steps) or "(none)"


def format_list(items: list[str]) -> str:
    return "\n".join(f"- {i}" for i in items) or "(none)"


def format_files(files: dict[str, str], max_chars: int = MAX_FILES_PROMPT_CHARS) -> str:
    """All files as ``### FILE:`` blocks (the coder's own format), capped in size."""
    if not files:
        return "(no files)"
    text = "\n\n".join(f"### FILE: {p}\n```\n{c}\n```" for p, c in files.items())
    return truncate(text, max_chars)


def exec_summary(r: ExecResult | None) -> str:
    """One line a model (or a person) can read: exit code plus abnormal-end flags."""
    if r is None:
        return "not run"
    parts = [f"exit code {r.exit_code}", f"{r.duration_s:.1f}s"]
    if r.timed_out:
        parts.append("timed out (killed at the time limit)")
    if r.oom_killed:
        parts.append("killed: out of memory")
    if r.disk_exceeded:
        parts.append("killed: disk limit exceeded")
    return ", ".join(parts)


def exec_streams(r: ExecResult | None) -> tuple[str, str]:
    """stdout/stderr trimmed for a prompt (already capped once by the executor)."""
    if r is None:
        return "(none)", "(none)"
    return (
        truncate(r.stdout, MAX_EXEC_PROMPT_CHARS) or "(empty)",
        truncate(r.stderr, MAX_EXEC_PROMPT_CHARS) or "(empty)",
    )


def event(node: str, usage: Usage | None = None, **extra: Any) -> dict[str, Any]:
    """The durable per-node record appended to ``events``.

    Token counts ride on events so the finalize step can total a run's usage
    without a shared tracker (a tracker reused across runs would over-count).
    """
    ev: dict[str, Any] = {"node": node}
    if usage is not None:
        ev["tokens_in"], ev["tokens_out"] = usage.tokens_in, usage.tokens_out
    ev.update(extra)
    return ev
