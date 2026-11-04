"""The contract between an eval system and the benchmark runner.

Definitions (shared by every system so numbers are comparable):

- ``attempts``: number of code generations, i.e. 1 + repairs (a graph replan
  counts as another generation).
- ``had_runtime_error``: any execution of the agent's own code during the run
  exited non-zero or timed out. A format failure ("no files" / "nothing to
  run") counts as a failed execution: it is reported to the model as exit 1.
  Systems that never execute report False.
- ``fixed``: ``had_runtime_error`` and the run ended with exit code 0 within
  ``max_repairs`` (3) repairs.
- ``first_try_pass``: the SYSTEM's own judgement of its first execution
  (exit code 0). ``None`` when the system never executes (SingleShot). The
  benchmark record's ``first_try_pass`` is different and authoritative: the
  runner grades ``first_files`` with the hidden tests.
- ``first_files``: the files produced by the first generation (attempt 1);
  ``None`` means "same as ``files``".
- ``budget_files``: the files of generation number ``max_repairs + 1`` (the 4th),
  or of the last generation if fewer were made; ``None`` means "same as
  ``files``". The runner grades them as ``matched_budget_pass`` so systems with
  different retry rules (the graph can replan and reset repairs) are comparable
  at the same number of generations.
- ``cost_usd``: ``None`` when any model used has no known price. Never 0.
"""
from dataclasses import asdict, dataclass
from typing import Any, Protocol

from coding_agent.config import Settings
from coding_agent.evaluation.task import Task
from coding_agent.llm import Usage


@dataclass(frozen=True)
class SystemOutput:
    files: dict[str, str]
    attempts: int
    first_try_pass: bool | None
    had_runtime_error: bool
    fixed: bool
    usage: Usage
    cost_usd: float | None
    wall_s: float
    error: str | None = None
    first_files: dict[str, str] | None = None  # None: same as ``files``
    budget_files: dict[str, str] | None = None  # None: same as ``files``


class System(Protocol):
    name: str

    def solve(self, task: Task) -> SystemOutput: ...

    def describe(self) -> dict[str, Any]:
        """``{"models": {...}, "settings": {...}}`` for the results file."""
        ...


def attach_partial(
    exc: BaseException, usage: Usage, cost_usd: float | None, wall_s: float
) -> None:
    """Record what a crashed run already spent on the exception, for the runner's crash record."""
    exc.partial_usage = usage  # type: ignore[attr-defined]
    exc.partial_cost_usd = cost_usd  # type: ignore[attr-defined]
    exc.partial_wall_s = wall_s  # type: ignore[attr-defined]


def settings_dict(settings: Settings) -> dict[str, Any]:
    """The run-shaping settings recorded in the results file (never the API key)."""
    return {
        "limits": asdict(settings.limits), "max_repairs": settings.max_repairs,
        "max_replans": settings.max_replans, "step_budget": settings.step_budget,
        "max_rpm": settings.max_rpm,
    }
