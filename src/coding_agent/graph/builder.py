"""Wires the agent nodes into the LangGraph state machine and runs it.

START -> planner -> architect -> coder -> executor -> reviewer, then a
conditional edge on ``route_after_review``: "coder" (repair), "planner"
(replan) or "end" -> finalize -> END. ``finalize`` is a real node (not logic in
``run_task``) so streaming callers (CLI, web UI) receive the FinalReport as the
last update, just like every other step.
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from coding_agent.agents import (
    make_architect,
    make_coder,
    make_executor,
    make_planner,
    make_reviewer,
)
from coding_agent.config import Settings
from coding_agent.graph.report import build_report
from coding_agent.graph.routing import route_after_review
from coding_agent.graph.state import AgentState, FinalReport, bump_visit, initial_state
from coding_agent.llm import ModelRouter
from coding_agent.sandbox import Sandbox

# LangGraph's own superstep cap, kept just above step_budget: the router ends
# the run at the budget, so hitting this would mean a routing bug.
RECURSION_MARGIN = 10


def build_graph(router: ModelRouter, sandbox: Sandbox, settings: Settings) -> CompiledStateGraph:
    """Compile the multi-agent graph with its dependencies injected.

    Models are fetched once per role here; the coder node gets both the
    "coder" and "debugger" models and picks by the last verdict.
    """

    def route(state: AgentState) -> str:
        return route_after_review(state, settings)

    def finalize(state: AgentState) -> dict[str, Any]:
        report = build_report(state, settings)
        return {
            "final": report, **bump_visit(state),
            "events": [{"node": "finalize", "success": report.success}],
        }

    graph = StateGraph(AgentState)
    graph.add_node("planner", make_planner(router.for_role("planner")))
    graph.add_node("architect", make_architect(router.for_role("architect")))
    graph.add_node("coder", make_coder(router.for_role("coder"), router.for_role("debugger")))
    graph.add_node("executor", make_executor(sandbox, settings))
    graph.add_node("reviewer", make_reviewer(router.for_role("reviewer")))
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "architect")
    graph.add_edge("architect", "coder")
    graph.add_edge("coder", "executor")
    graph.add_edge("executor", "reviewer")
    graph.add_conditional_edges(
        "reviewer", route, {"coder": "coder", "planner": "planner", "end": "finalize"}
    )
    graph.add_edge("finalize", END)
    return graph.compile().with_config(recursion_limit=settings.step_budget + RECURSION_MARGIN)


def stream_task(graph: CompiledStateGraph, task: str) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield ``(node_name, partial_update)`` as each node finishes, for live UIs."""
    for chunk in graph.stream(initial_state(task), stream_mode="updates"):
        yield from chunk.items()


def run_graph(graph: CompiledStateGraph, task: str) -> AgentState:
    """Run to completion and return the final state (events, code versions, final)."""
    return graph.invoke(initial_state(task))


def run_task(graph: CompiledStateGraph, task: str) -> FinalReport:
    """Run to completion and return just the FinalReport."""
    return run_graph(graph, task)["final"]
