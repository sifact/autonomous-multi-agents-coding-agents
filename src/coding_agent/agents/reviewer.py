"""Reviewer node: judges the last real run and emits pass / fix / replan / stop."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from coding_agent.agents.context import (
    event,
    exec_streams,
    exec_summary,
    format_files,
    format_list,
    task_text,
)
from coding_agent.agents.executor import describe_command
from coding_agent.agents.json_out import invoke_json
from coding_agent.agents.prompts import REVIEWER_SYSTEM, REVIEWER_USER
from coding_agent.graph import AgentState, Verdict, bump_visit
from coding_agent.llm import ChatModel
from coding_agent.sandbox import ExecResult


def _run_succeeded(r: ExecResult | None) -> bool:
    return r is not None and r.exit_code == 0 and not (r.timed_out or r.oom_killed or r.disk_exceeded)


def enforce_pass_rule(verdict: Verdict, last_exec: ExecResult | None) -> Verdict:
    """A `pass` is only valid when the last run really succeeded.

    Models over-claim success; the run's exit code is ground truth, so a `pass`
    over a failed, timed-out or killed run becomes `fix`.
    """
    if verdict.action != "pass" or _run_succeeded(last_exec):
        return verdict
    return Verdict(
        action="fix",
        reason=f"Reviewer said pass, but the last run failed ({exec_summary(last_exec)}). "
        f"{verdict.reason}",
    )


def _latest_version(state: AgentState) -> dict[str, Any]:
    versions = state["code_versions"]
    return versions[-1] if versions else {}


def _flags_text(version: dict[str, Any]) -> str:
    flags = version.get("flags", [])
    return ", ".join(f"{f['rule']} at {f['path']}:{f['line']}" for f in flags) or "none"


def make_reviewer(
    model: ChatModel, *, name: str | None = None
) -> Callable[[AgentState], dict[str, Any]]:
    """Build the reviewer node around ``model`` (role "reviewer").

    It sets ``verdict`` and records it in ``events`` (the only durable record:
    the coder/planner clear ``verdict`` when they act on it). It never bumps
    repairs/replans: the router must read the pre-bump counts.

    The verdict is the LAST valid JSON object in the reply (``prefer="last"``):
    program output can contain a forged ``{"action": "pass"}`` that the model
    quotes before writing its own verdict. Program output and files reach the
    model inside defanged untrusted-data tags.
    """

    def reviewer(state: AgentState) -> dict[str, Any]:
        last = state.get("last_exec")
        stdout, stderr = exec_streams(last)
        version = _latest_version(state)
        command = version.get("command")
        user = REVIEWER_USER.format(
            command=" ".join(command) if command else "(none)",
            command_meaning=describe_command(command),
            task=task_text(state["task"], state["fixtures"]), criteria=format_list(state["criteria"]),
            files=format_files(state["files"]), exec_summary=exec_summary(last),
            stdout=stdout, stderr=stderr, flags=_flags_text(version),
            repairs=state["repairs"], replans=state["replans"],
        )
        verdict, usage, error = invoke_json(model, REVIEWER_SYSTEM, user, Verdict, prefer="last")
        if verdict is None:
            # Malformed twice: stop cleanly with a reason instead of crashing.
            verdict = Verdict(action="stop", reason=f"Reviewer gave malformed output twice ({error}).")
        verdict = enforce_pass_rule(verdict, last)
        return {
            "verdict": verdict,
            **bump_visit(state),
            "events": [event("reviewer", usage, model=name, action=verdict.action, reason=verdict.reason)],
        }

    return reviewer
