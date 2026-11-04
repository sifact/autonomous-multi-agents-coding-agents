"""Coder node: writes the files on the first pass and repairs them (as debugger) after `fix`.

Output format: ``### FILE: path`` followed by one fenced block per file. Code in
a delimiter format survives small models far better than code escaped inside
JSON strings; ``{"files": {"path": "content"}}`` JSON is still accepted as a
fallback because it costs one ``parse_json`` call.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import PurePosixPath
from typing import Any

from pydantic import BaseModel

from coding_agent.agents.context import (
    event,
    exec_streams,
    exec_summary,
    format_files,
    format_list,
    format_plan,
    task_text,
)
from coding_agent.agents.json_out import ParseError, parse_json
from coding_agent.agents.prompts import CODER_SYSTEM, CODER_USER, DEBUGGER_SYSTEM, DEBUGGER_USER
from coding_agent.graph import AgentState, apply_verdict_counters, bump_visit
from coding_agent.llm import ChatModel

_FILE_HEADER = re.compile(r"^#{2,4}\s*FILE:\s*(.+?)\s*$", re.MULTILINE)
_FENCE_LINE = re.compile(r"^\s*```")
_BARE_FENCE = re.compile(r"`{3,}")


class CodeFiles(BaseModel):
    files: dict[str, str]


def _section_body(section: str) -> str:
    """Content of the first fenced block; the LAST bare fence closes it, so a
    ``` inside a string literal on a code line cannot end the file early."""
    lines = section.splitlines()
    opens = [i for i, ln in enumerate(lines) if _FENCE_LINE.match(ln)]
    if len(opens) < 2:
        return section.strip() + "\n"
    closes = [i for i in opens[1:] if _BARE_FENCE.fullmatch(lines[i].strip())]
    end = closes[-1] if closes else opens[-1]
    return "\n".join(lines[opens[0] + 1 : end]) + "\n"


def _is_usable_path(path: str) -> bool:
    # '', '.', './' name the workspace itself, never a file.
    return bool(PurePosixPath(path).parts)


def split_files(text: str) -> tuple[dict[str, str], list[str]]:
    """``(files, dropped_paths)`` from coder output; unusable paths are dropped."""
    headers = list(_FILE_HEADER.finditer(text))
    if headers:
        raw = {}
        for h, nxt in zip(headers, [*headers[1:], None], strict=True):
            path = h.group(1).strip("`'\" ")
            raw[path] = _section_body(text[h.end() : nxt.start() if nxt else len(text)])
    else:
        try:
            raw = parse_json(text, CodeFiles).files
        except ParseError:
            raw = {}
    files = {p: c for p, c in raw.items() if _is_usable_path(p)}
    return files, [p for p in raw if p not in files]


def parse_files(text: str) -> dict[str, str]:
    """Extract ``{path: content}`` from coder output; ``{}`` when nothing is found."""
    return split_files(text)[0]


def make_coder(
    model: ChatModel,
    debugger: ChatModel | None = None,
    *,
    name: str | None = None,
    debugger_name: str | None = None,
) -> Callable[[AgentState], dict[str, Any]]:
    """Build the coder node: ``model`` (role "coder") writes, ``debugger`` (role
    "debugger", defaults to ``model``) repairs when the last verdict was ``fix``.
    ``name``/``debugger_name`` are the resolved model names recorded on events."""
    repairer = debugger or model
    repairer_name = debugger_name if debugger is not None else name

    def coder(state: AgentState) -> dict[str, Any]:
        # Read verdict and last_exec BEFORE building the update:
        # apply_verdict_counters clears the verdict.
        verdict = state.get("verdict")
        repairing = verdict is not None and verdict.action == "fix"
        if repairing:
            stdout, stderr = exec_streams(state.get("last_exec"))
            user = DEBUGGER_USER.format(
                task=task_text(state["task"], state["fixtures"]), criteria=format_list(state["criteria"]),
                files=format_files(state["files"]), exec_summary=exec_summary(state.get("last_exec")),
                stdout=stdout, stderr=stderr, reason=verdict.reason or "(none)",
            )
            resp = repairer.invoke(DEBUGGER_SYSTEM, user)
        else:
            user = CODER_USER.format(
                task=task_text(state["task"], state["fixtures"]), plan=format_plan(state["plan"]),
                criteria=format_list(state["criteria"]), layout=format_list(state["layout"]),
            )
            resp = model.invoke(CODER_SYSTEM, user)
        files, dropped = split_files(resp.text)
        role = "debugger" if repairing else "coder"
        extra: dict[str, Any] = {"role": role, "files": sorted(files)}
        if dropped:
            extra["dropped_paths"] = dropped
        return {
            "files": files,
            **(apply_verdict_counters(state) if repairing else {}),
            **bump_visit(state),
            "events": [event(
                "coder", resp.usage, model=repairer_name if repairing else name, **extra
            )],
        }

    return coder
