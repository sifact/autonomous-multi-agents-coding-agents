"""Planner node: turns the task (or a failed plan) into steps and acceptance criteria."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from coding_agent.agents.context import event, exec_streams, format_plan
from coding_agent.agents.json_out import invoke_json
from coding_agent.agents.prompts import PLANNER_REPLAN, PLANNER_SYSTEM, PLANNER_USER
from coding_agent.graph import AgentState, Step, apply_verdict_counters, bump_visit
from coding_agent.llm import ChatModel

FALLBACK_CRITERIA = ["The program runs to completion with exit code 0."]


class Plan(BaseModel):
    """The planner's JSON reply."""

    steps: list[Step] = Field(min_length=1)
    criteria: list[str] = Field(default_factory=list)


def _fallback(task: str) -> Plan:
    # Two malformed replies must not crash the run: one step that restates the
    # task still lets the coder and reviewer do useful work.
    return Plan(
        steps=[Step(id=1, description=task, acceptance=FALLBACK_CRITERIA[0])],
        criteria=FALLBACK_CRITERIA,
    )


def make_planner(
    model: ChatModel, *, name: str | None = None
) -> Callable[[AgentState], dict[str, Any]]:
    """Build the planner node around ``model`` (role "planner"; ``name`` goes on events)."""

    def planner(state: AgentState) -> dict[str, Any]:
        # Read the verdict BEFORE building the update: apply_verdict_counters
        # clears it, and only a `replan` verdict makes this a replan.
        verdict = state.get("verdict")
        replanning = verdict is not None and verdict.action == "replan"
        replan = ""
        if replanning:
            _, stderr = exec_streams(state.get("last_exec"))
            replan = PLANNER_REPLAN.format(
                previous_plan=format_plan(state["plan"]), reason=verdict.reason, stderr=stderr
            )
        plan, usage, error = invoke_json(
            model, PLANNER_SYSTEM, PLANNER_USER.format(task=state["task"], replan=replan), Plan
        )
        fallback = plan is None
        if plan is None:
            plan = _fallback(state["task"])
        criteria = plan.criteria or [s.acceptance for s in plan.steps]
        extra: dict[str, Any] = {
            "model": name, "steps": len(plan.steps), "replan": replanning, "fallback": fallback,
        }
        if error:
            extra["error"] = error
        return {
            "plan": plan.steps,
            "criteria": criteria,
            **(apply_verdict_counters(state) if replanning else {}),
            **bump_visit(state),
            "events": [event("planner", usage, **extra)],
        }

    return planner
