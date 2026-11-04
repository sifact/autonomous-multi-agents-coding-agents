"""Graph layer: state, value types, routing, report and the compiled graph.

``builder`` and ``report`` import ``coding_agent.agents``, which imports this
package for the state types. Their names are therefore resolved lazily (PEP
562 ``__getattr__``) so importing either package first never hits a cycle.
"""
from importlib import import_module
from typing import Any

from coding_agent.graph.routing import Route, route_after_review, stop_reason
from coding_agent.graph.state import (
    AgentState,
    FinalReport,
    Step,
    Verdict,
    apply_verdict_counters,
    bump_visit,
    initial_state,
)

_LAZY = {
    "build_graph": "coding_agent.graph.builder",
    "run_graph": "coding_agent.graph.builder",
    "run_task": "coding_agent.graph.builder",
    "stream_task": "coding_agent.graph.builder",
    "build_report": "coding_agent.graph.report",
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        return getattr(import_module(_LAZY[name]), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AgentState",
    "FinalReport",
    "Route",
    "Step",
    "Verdict",
    "apply_verdict_counters",
    "build_graph",
    "build_report",
    "bump_visit",
    "initial_state",
    "route_after_review",
    "run_graph",
    "run_task",
    "stop_reason",
    "stream_task",
]
