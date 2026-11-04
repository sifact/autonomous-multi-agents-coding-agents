"""Shared graph state and the small value types that flow through it."""
from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

from pydantic import BaseModel, field_validator

from coding_agent.llm import Usage
from coding_agent.sandbox import ExecResult

MAX_REASON_CHARS = 500


class Step(BaseModel):
    """One planned unit of work with a checkable acceptance condition."""

    id: int
    description: str
    acceptance: str


class Verdict(BaseModel):
    """Reviewer decision. Parseable straight from model JSON."""

    action: Literal["pass", "fix", "replan", "stop"]
    reason: str = ""

    @field_validator("action", mode="before")
    @classmethod
    def _normalise_action(cls, v: object) -> object:
        # Models vary case and whitespace; an action that is still not one of
        # the four values fails validation.
        return v.strip().lower() if isinstance(v, str) else v

    @field_validator("reason")
    @classmethod
    def _clip(cls, v: str) -> str:
        # Models ramble; clip an over-long reason instead of failing validation.
        return v[:MAX_REASON_CHARS]


class FinalReport(BaseModel):
    """What the run hands back to the caller."""

    success: bool
    files: dict[str, str]
    explanation: str
    repairs: int
    usage: Usage


class AgentState(TypedDict):
    """Graph state. Scalars overwrite; ``events`` appends via its reducer."""

    task: str
    fixtures: dict[str, str]  # read-only data files present at run time
    plan: list[Step]
    criteria: list[str]
    layout: list[str]
    files: dict[str, str]
    code_versions: list[dict]
    last_exec: ExecResult | None
    verdict: Verdict | None
    repairs: int
    replans: int
    visits: int
    events: Annotated[list, operator.add]
    final: FinalReport | None


def initial_state(task: str, fixtures: dict[str, str] | None = None) -> AgentState:
    """Fresh state: counters at zero, containers empty and unshared."""
    return AgentState(
        task=task, fixtures=dict(fixtures or {}), plan=[], criteria=[], layout=[], files={}, code_versions=[],
        last_exec=None, verdict=None, repairs=0, replans=0, visits=0,
        events=[], final=None,
    )


def bump_visit(state: AgentState) -> dict[str, Any]:
    """Partial update counting one node visit.

    EVERY node (planner, architect, coder, executor, reviewer) includes this
    in its returned update. With default limits the worst case is about 39
    visits, so ``step_budget`` (40) is a real backstop, not a decoration.
    """
    return {"visits": state["visits"] + 1}


def apply_verdict_counters(state: AgentState) -> dict[str, Any]:
    """Partial update recording the repair/replan the last verdict triggers.

    ``repairs``/``replans`` count work already performed, and the router reads
    them after the reviewer and BEFORE any bump. So this is called by the node
    that performs the work: the coder when the last verdict was ``fix``, the
    planner when it was ``replan``. NEVER call it from the reviewer node:
    LangGraph applies a node's update before running its conditional edge, so
    the router would see the bumped count and end one attempt early.

    fix -> repairs+1; replan -> replans+1 and repairs reset to 0 (a new plan
    gets a fresh repair allowance). Both also return ``verdict: None`` so the
    same verdict can never be counted twice (the caller reads the verdict
    before building its update). pass/stop/no verdict return ``{}``.
    """
    v = state.get("verdict")
    if v is None:
        return {}
    if v.action == "fix":
        return {"repairs": state["repairs"] + 1, "verdict": None}
    if v.action == "replan":
        return {"replans": state["replans"] + 1, "repairs": 0, "verdict": None}
    return {}
