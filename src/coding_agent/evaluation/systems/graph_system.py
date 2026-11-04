"""The multi-agent graph as an eval system."""
import time
from collections.abc import Callable
from typing import Any, get_args

from coding_agent.config import Settings
from coding_agent.evaluation.prompting import task_prompt
from coding_agent.evaluation.systems.base import SystemOutput, attach_partial, settings_dict
from coding_agent.evaluation.task import Task
from coding_agent.graph import build_graph, run_graph
from coding_agent.llm import ModelRouter, Role, Usage, UsageTracker
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
        self._resolved_roles: dict[str, str] = {}

    def solve(self, task: Task) -> SystemOutput:
        start = time.monotonic()
        tracker = UsageTracker()
        try:
            router = self._router_factory(tracker)
            self._resolved_roles = {role: router.model_name(role) for role in get_args(Role)}
            graph = build_graph(router, self._sandbox, self._settings)
            state = run_graph(graph, task_prompt(task, with_fixtures=False), task.fixtures)
        except Exception as exc:
            spent = sum(tracker.by_model.values(), Usage(0, 0))
            attach_partial(exc, spent, tracker.total_cost, time.monotonic() - start)
            raise
        versions = state["code_versions"]
        files = dict(state["final"].files)
        attempts = max(1, sum(1 for e in state["events"] if e["node"] == "coder"))
        failed = [v["exit_code"] != 0 or v["timed_out"] for v in versions]
        had_error = any(failed)
        last_ok = bool(versions) and not failed[-1]
        budget_index = min(len(versions) - 1, self._settings.max_repairs)
        return SystemOutput(
            files=files, attempts=attempts,
            first_try_pass=(not failed[0]) if versions else False,
            had_runtime_error=had_error,
            fixed=had_error and last_ok and attempts - 1 <= self._settings.max_repairs,
            usage=state["final"].usage,
            cost_usd=tracker.total_cost, wall_s=time.monotonic() - start,
            first_files=dict(versions[0]["files"]) if versions else {},
            budget_files=dict(versions[budget_index]["files"]) if versions else files,
        )

    def describe(self) -> dict[str, Any]:
        s = self._settings
        info: dict[str, Any] = {
            "models": {"cheap": s.model_cheap, "strong": s.model_strong},
            "settings": settings_dict(s),
        }
        if self._resolved_roles:  # what the router actually resolved on the last run
            info["resolved_roles"] = dict(self._resolved_roles)
        return info
