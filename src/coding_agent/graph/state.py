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
    reason: str

    @field_validator("reason")
    @classmethod
    def _clip(cls, v: str) -> str:
        # Models ramble; clip instead of failing so a good action is not lost.
        return v[:MAX_REASON_CHARS]


class FinalReport(BaseModel):
    """What the run hands back to the caller."""

    success: bool
    files: dict[str, str]
    explanation: str
    repairs: int
    usage: Usage

    model_config = {"arbitrary_types_allowed": True}


class AgentState(TypedDict):
    """Graph state. Scalars overwrite; ``events`` appends via its reducer."""

    task: str
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


def initial_state(task: str) -> AgentState:
    """Fresh state: counters at zero, containers empty and unshared."""
    return AgentState(
        task=task, plan=[], criteria=[], layout=[], files={}, code_versions=[],
        last_exec=None, verdict=None, repairs=0, replans=0, visits=0,
        events=[], final=None,
    )


def apply_verdict_counters(state: AgentState) -> dict[str, Any]:
    """Partial update bumping the counters a verdict implies.

    fix -> repairs+1; replan -> replans+1 and repairs reset to 0 (a new plan
    gets a fresh repair allowance); pass/stop/no verdict -> nothing.
    """
    v = state.get("verdict")
    if v is None:
        return {}
    if v.action == "fix":
        return {"repairs": state["repairs"] + 1}
    if v.action == "replan":
        return {"replans": state["replans"] + 1, "repairs": 0}
    return {}
