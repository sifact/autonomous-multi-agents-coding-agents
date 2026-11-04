"""Turns the final graph state into the FinalReport handed back to callers."""
from __future__ import annotations

from coding_agent.agents.context import exec_summary
from coding_agent.agents.prompts import MAX_REPORT_ERROR_CHARS
from coding_agent.config import Settings
from coding_agent.graph.routing import stop_reason
from coding_agent.graph.state import AgentState, FinalReport
from coding_agent.llm import Usage
from coding_agent.sandbox import ExecResult


def run_usage(state: AgentState) -> Usage:
    """Tokens of THIS run, summed from node events (a shared tracker spans runs)."""
    events = state["events"]
    return Usage(
        sum(e.get("tokens_in", 0) for e in events), sum(e.get("tokens_out", 0) for e in events)
    )


def _error_text(r: ExecResult) -> str:
    # Tracebacks go to stderr; pytest reports failures on stdout.
    return r.stderr if r.stderr.strip() else r.stdout


def last_error_line(r: ExecResult | None) -> str:
    """Last non-blank line of the error output: the exception line of a traceback."""
    if r is None:
        return ""
    lines = [ln.strip() for ln in _error_text(r).splitlines() if ln.strip()]
    return lines[-1][:MAX_REPORT_ERROR_CHARS] if lines else ""


def _failure_explanation(state: AgentState, settings: Settings) -> str:
    reason = stop_reason(state, settings) or "The run ended without a passing review."
    last = state.get("last_exec")
    if last is None:
        return f"{reason} No code was run."
    parts = [reason, f"Last run: {exec_summary(last)}."]
    line = last_error_line(last)
    if line:
        parts.append(f"Last error: {line}")
    tail = _error_text(last).strip()[-MAX_REPORT_ERROR_CHARS:]
    if tail and tail != line:
        parts.append(f"\nError output (tail):\n{tail}")
    return " ".join(parts)


def build_report(state: AgentState, settings: Settings) -> FinalReport:
    """Success iff the final verdict is `pass` (the reviewer already enforced exit code 0)."""
    verdict = state.get("verdict")
    success = verdict is not None and verdict.action == "pass"
    if success:
        explanation = (
            f"Passed after {state['repairs']} repair(s) and {state['replans']} replan(s): "
            f"{verdict.reason}"
        )
    else:
        explanation = _failure_explanation(state, settings)
    return FinalReport(
        success=success, files=dict(state["files"]), explanation=explanation,
        repairs=state["repairs"], usage=run_usage(state),
    )
