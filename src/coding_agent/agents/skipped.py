"""Zero-cost stand-ins for the planner and architect, used by the ablation variants.

A skipped role makes no model call but still behaves like the node it replaces for
the graph's bookkeeping: it bumps ``visits`` (so the step budget stays real) and
the skipped planner still applies the replan counters (so a reviewer that keeps
saying ``replan`` ends after ``max_replans`` instead of looping). Its event
carries ``skipped: True`` and zero tokens, which keeps run usage honest.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from coding_agent.agents.context import event
from coding_agent.graph import AgentState, Step, apply_verdict_counters, bump_visit
from coding_agent.llm import Usage

SKIPPED_CRITERION = "the program runs and does what the task asks"


def make_skipped_planner() -> Callable[[AgentState], dict[str, Any]]:
    """Planner stand-in: one step holding the task text and a single generic criterion."""

    def planner(state: AgentState) -> dict[str, Any]:
        verdict = state.get("verdict")
        replanning = verdict is not None and verdict.action == "replan"
        step = Step(id=1, description=state["task"], acceptance=SKIPPED_CRITERION)
        return {
            "plan": [step], "criteria": [SKIPPED_CRITERION],
            **(apply_verdict_counters(state) if replanning else {}),
            **bump_visit(state),
            "events": [event("planner", Usage(0, 0), skipped=True, replan=replanning)],
        }

    return planner


def make_skipped_architect() -> Callable[[AgentState], dict[str, Any]]:
    """Architect stand-in: an empty layout, which means "the coder decides the files"."""

    def architect(state: AgentState) -> dict[str, Any]:
        return {
            "layout": [], **bump_visit(state),
            "events": [event("architect", Usage(0, 0), skipped=True)],
        }

    return architect
