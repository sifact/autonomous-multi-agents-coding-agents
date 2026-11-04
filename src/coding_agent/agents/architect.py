"""Architect node: picks the files (and their purpose) the coder must write."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from coding_agent.agents.context import event, format_list, format_plan
from coding_agent.agents.json_out import invoke_json
from coding_agent.agents.prompts import ARCHITECT_SYSTEM, ARCHITECT_USER, DEFAULT_ENTRYPOINT
from coding_agent.graph import AgentState, bump_visit
from coding_agent.llm import ChatModel


class FileSpec(BaseModel):
    path: str
    purpose: str = ""


class Layout(BaseModel):
    """The architect's JSON reply."""

    files: list[FileSpec] = Field(min_length=1)


def make_architect(
    model: ChatModel, *, name: str | None = None
) -> Callable[[AgentState], dict[str, Any]]:
    """Build the architect node around ``model`` (role "architect"; ``name`` goes on events)."""

    def architect(state: AgentState) -> dict[str, Any]:
        user = ARCHITECT_USER.format(
            task=state["task"], plan=format_plan(state["plan"]), criteria=format_list(state["criteria"])
        )
        layout, usage, error = invoke_json(model, ARCHITECT_SYSTEM, user, Layout)
        if layout is None:
            # Malformed twice: a single entry point is the safe default layout.
            paths = [DEFAULT_ENTRYPOINT]
        else:
            paths = [f"{f.path}: {f.purpose}" if f.purpose else f.path for f in layout.files]
        extra: dict[str, Any] = {"model": name, "files": len(paths), "fallback": layout is None}
        if error:
            extra["error"] = error
        return {"layout": paths, **bump_visit(state), "events": [event("architect", usage, **extra)]}

    return architect
