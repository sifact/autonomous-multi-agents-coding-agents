"""The multi-agent graph as an eval system."""
import time
from collections.abc import Callable
from typing import Any

from coding_agent.config import Settings
from coding_agent.evaluation.prompting import task_prompt
from coding_agent.evaluation.systems.base import SystemOutput, settings_dict
from coding_agent.evaluation.task import Task
from coding_agent.graph import build_graph, run_graph
from coding_agent.llm import ModelRouter, UsageTracker
from coding_agent.sandbox import Sandbox


class GraphSystem:
    """Wraps ``build_graph``/``run_graph``.

    ``router_factory(tracker)`` is called once PER TASK with a brand-new
    ``UsageTracker`` so tokens and cost are per-run and comparable with the
    baselines (a tracker shared across tasks would accumulate).
    """

    name = "graph"

    def __init__(
        self, router_factory: Callable[[UsageTracker], ModelRouter], sandbox: Sandbox,
        settings: Settings,
    ) -> None:
        self._router_factory, self._sandbox, self._settings = router_factory, sandbox, settings

    def solve(self, task: Task) -> SystemOutput:
        start = time.monotonic()
        tracker = UsageTracker()
        graph = build_graph(self._router_factory(tracker), self._sandbox, self._settings)
        state = run_graph(graph, task_prompt(task))
        versions = state["code_versions"]
        attempts = max(1, sum(1 for e in state["events"] if e["node"] == "coder"))
        failed = [v["exit_code"] != 0 or v["timed_out"] for v in versions]
        had_error = any(failed)
        last_ok = bool(versions) and not failed[-1]
        return SystemOutput(
            files=dict(state["final"].files), attempts=attempts,
            first_try_pass=(not failed[0]) if versions else False,
            had_runtime_error=had_error,
            fixed=had_error and last_ok and attempts - 1 <= self._settings.max_repairs,
            usage=state["final"].usage,
            cost_usd=tracker.total_cost, wall_s=time.monotonic() - start,
            first_files=dict(versions[0]["files"]) if versions else {},
        )

    def describe(self) -> dict[str, Any]:
        s = self._settings
        return {
            "models": {"cheap": s.model_cheap, "strong": s.model_strong},
            "settings": settings_dict(s),
        }
