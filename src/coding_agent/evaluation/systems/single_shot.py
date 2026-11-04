"""Baseline 1: one model call, no execution, no feedback."""
import time
from typing import Any

from coding_agent.agents import split_files
from coding_agent.agents.prompts import BASELINE_USER, CODER_SYSTEM
from coding_agent.evaluation.prompting import task_prompt
from coding_agent.evaluation.systems.base import SystemOutput
from coding_agent.evaluation.task import Task
from coding_agent.llm import ChatModel, cost_usd
from coding_agent.sandbox import Sandbox


class SingleShot:
    """Ask once, take whatever comes back. The sandbox is accepted for a uniform
    constructor but is never used: this system cannot see its own errors."""

    name = "single_shot"

    def __init__(self, model: ChatModel, sandbox: Sandbox, model_name: str = "unknown") -> None:
        self._model, self._sandbox, self._model_name = model, sandbox, model_name

    def solve(self, task: Task) -> SystemOutput:
        start = time.monotonic()
        resp = self._model.invoke(CODER_SYSTEM, BASELINE_USER.format(task=task_prompt(task)))
        files = split_files(resp.text)[0]
        return SystemOutput(
            files=files, attempts=1, first_try_pass=None, had_runtime_error=False, fixed=False,
            usage=resp.usage, cost_usd=cost_usd(self._model_name, resp.usage),
            wall_s=time.monotonic() - start, first_files=dict(files),
        )

    def describe(self) -> dict[str, Any]:
        return {"models": {"model": self._model_name}, "settings": {"max_repairs": 0}}
