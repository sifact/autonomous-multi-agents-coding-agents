"""Coder node: writes the files on the first pass and repairs them (as debugger) after `fix`.

Output format: ``### FILE: path`` followed by one fenced block per file. Code in
a delimiter format survives small models far better than code escaped inside
JSON strings; ``{"files": {"path": "content"}}`` JSON is still accepted as a
fallback because it costs one ``parse_json`` call.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from coding_agent.agents.context import (
    event,
    exec_streams,
    exec_summary,
    format_files,
    format_list,
    format_plan,
)
from coding_agent.agents.json_out import ParseError, parse_json
from coding_agent.agents.prompts import CODER_SYSTEM, CODER_USER, DEBUGGER_SYSTEM, DEBUGGER_USER
from coding_agent.graph import AgentState, apply_verdict_counters, bump_visit
from coding_agent.llm import ChatModel

_FILE_HEADER = re.compile(r"^#{2,4}\s*FILE:\s*(.+?)\s*$", re.MULTILINE)
_FENCE_LINE = re.compile(r"^\s*```")


class CodeFiles(BaseModel):
    files: dict[str, str]


def _section_body(section: str) -> str:
    """Content of the first fenced block; the LAST bare fence closes it, so a
    ``` inside a string literal on a code line cannot end the file early."""
    lines = section.splitlines()
    opens = [i for i, ln in enumerate(lines) if _FENCE_LINE.match(ln)]
    if len(opens) < 2:
        return section.strip() + "\n"
    closes = [i for i in opens[1:] if lines[i].strip() == "```"]
    end = closes[-1] if closes else opens[-1]
    return "\n".join(lines[opens[0] + 1 : end]) + "\n"


def parse_files(text: str) -> dict[str, str]:
    """Extract ``{path: content}`` from coder output; ``{}`` when nothing is found."""
    headers = list(_FILE_HEADER.finditer(text))
    if headers:
        files = {}
        for h, nxt in zip(headers, [*headers[1:], None], strict=True):
            path = h.group(1).strip("`'\" ")
            files[path] = _section_body(text[h.end() : nxt.start() if nxt else len(text)])
        return files
    try:
        return parse_json(text, CodeFiles).files
    except ParseError:
        return {}


def make_coder(
    model: ChatModel, debugger: ChatModel | None = None
) -> Callable[[AgentState], dict[str, Any]]:
    """Build the coder node: ``model`` (role "coder") writes, ``debugger`` (role
    "debugger", defaults to ``model``) repairs when the last verdict was ``fix``."""
    repairer = debugger or model

    def coder(state: AgentState) -> dict[str, Any]:
        # Read verdict and last_exec BEFORE building the update:
        # apply_verdict_counters clears the verdict.
        verdict = state.get("verdict")
        repairing = verdict is not None and verdict.action == "fix"
        if repairing:
            stdout, stderr = exec_streams(state.get("last_exec"))
            user = DEBUGGER_USER.format(
                task=state["task"], criteria=format_list(state["criteria"]),
                files=format_files(state["files"]), exec_summary=exec_summary(state.get("last_exec")),
                stdout=stdout, stderr=stderr, reason=verdict.reason or "(none)",
            )
            resp = repairer.invoke(DEBUGGER_SYSTEM, user)
        else:
            user = CODER_USER.format(
                task=state["task"], plan=format_plan(state["plan"]),
                criteria=format_list(state["criteria"]), layout=format_list(state["layout"]),
            )
            resp = model.invoke(CODER_SYSTEM, user)
        files = parse_files(resp.text)
        role = "debugger" if repairing else "coder"
        return {
            "files": files,
            **(apply_verdict_counters(state) if repairing else {}),
            **bump_visit(state),
            "events": [event("coder", resp.usage, role=role, files=sorted(files))],
        }

    return coder
