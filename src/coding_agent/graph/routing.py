"""Pure routing after the reviewer: where the graph goes next, and why it stops."""
from __future__ import annotations

from typing import Literal

from coding_agent.config import Settings
from coding_agent.graph.state import AgentState

Route = Literal["coder", "planner", "end"]


def route_after_review(state: AgentState, settings: Settings) -> Route:
    """Pick the next node.

    ``repairs`` / ``replans`` count repairs/replans already performed; this
    reads state after the reviewer and BEFORE any bump. The bump is applied by
    the coder (on ``fix``) or planner (on ``replan``) via
    ``apply_verdict_counters``, never by the reviewer, because LangGraph applies
    a node's update before its conditional edge runs. With max_repairs=3,
    repairs 0..2 plus ``fix`` goes to the coder; repairs==3 plus ``fix`` ends.
    Every node bumps ``visits`` (``bump_visit``) so the step budget is real.
    """
    if state["visits"] >= settings.step_budget:
        return "end"
    v = state.get("verdict")
    action = getattr(v, "action", None)
    if action == "fix" and state["repairs"] < settings.max_repairs:
        return "coder"
    if action == "replan" and state["replans"] < settings.max_replans:
        return "planner"
    return "end"


def stop_reason(state: AgentState, settings: Settings) -> str | None:
    """Human-readable cause when the run ends unsuccessfully, else None.

    Call only after ``route_after_review`` returned "end".
    """
    v = state.get("verdict")
    action = getattr(v, "action", None)
    if action == "pass":
        return None
    if state["visits"] >= settings.step_budget:
        return f"Step budget of {settings.step_budget} exhausted."
    if v is None:
        return "Reviewer produced no verdict."
    if action == "fix":
        if state["repairs"] >= settings.max_repairs:
            return f"Repair limit of {settings.max_repairs} reached; last issue: {v.reason}"
        return None
    if action == "replan":
        if state["replans"] >= settings.max_replans:
            return f"Replan limit of {settings.max_replans} reached; last issue: {v.reason}"
        return None
    if action == "stop":
        return f"Reviewer stopped the run: {v.reason}"
    return f"Unknown reviewer action {action!r}."
