"""The contract between an eval system and the benchmark runner.

Definitions (shared by every system so numbers are comparable):

- ``attempts``: number of code generations, i.e. 1 + repairs (a graph replan
  counts as another generation).
- ``had_runtime_error``: any execution of the agent's own code during the run
  exited non-zero or timed out. Systems that never execute report False.
- ``fixed``: ``had_runtime_error`` and the run ended with exit code 0 within
  ``max_repairs`` (3) repairs.
- ``first_try_pass``: the SYSTEM's own judgement of its first execution
  (exit code 0). ``None`` when the system never executes (SingleShot). The
  benchmark record's ``first_try_pass`` is different and authoritative: the
  runner grades ``first_files`` with the hidden tests.
- ``first_files``: the files produced by the first generation (attempt 1);
  ``None`` means "same as ``files``".
- ``cost_usd``: ``None`` when any model used has no known price. Never 0.
"""
from dataclasses import asdict, dataclass
from typing import Any, Protocol

from coding_agent.config import Settings
from coding_agent.evaluation.task import Task
from coding_agent.llm import Usage

DEFAULT_MAX_REPAIRS = 3


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


class System(Protocol):
    name: str

    def solve(self, task: Task) -> SystemOutput: ...

    def describe(self) -> dict[str, Any]:
        """``{"models": {...}, "settings": {...}}`` for the results file."""
        ...


def settings_dict(settings: Settings) -> dict[str, Any]:
    """The run-shaping settings recorded in the results file (never the API key)."""
    return {
        "limits": asdict(settings.limits), "max_repairs": settings.max_repairs,
        "max_replans": settings.max_replans, "step_budget": settings.step_budget,
        "max_rpm": settings.max_rpm,
    }
