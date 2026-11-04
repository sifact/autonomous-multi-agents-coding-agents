"""Baseline 2: one agent that generates, runs, and repairs with the same model."""
import time
from typing import Any

from coding_agent.agents import execute_files, split_files
from coding_agent.agents.context import exec_streams, exec_summary, format_files
from coding_agent.agents.prompts import (
    BASELINE_REPAIR_USER,
    BASELINE_USER,
    CODER_SYSTEM,
    DEBUGGER_SYSTEM,
)
from coding_agent.config import Settings
from coding_agent.evaluation.prompting import task_prompt
from coding_agent.evaluation.systems.base import DEFAULT_MAX_REPAIRS, SystemOutput, settings_dict
from coding_agent.evaluation.task import Task
from coding_agent.llm import ChatModel, cost_usd
from coding_agent.sandbox import ExecResult, Sandbox


def _failed(r: ExecResult) -> bool:
    return r.exit_code != 0 or r.timed_out


class SingleAgentLoop:
    """Generate, execute (same mechanics as the graph's executor), and on failure feed the
    truncated output back to the same model, up to ``max_repairs`` times."""

    name = "single_agent"

    def __init__(
        self, model: ChatModel, sandbox: Sandbox, settings: Settings,
        max_repairs: int = DEFAULT_MAX_REPAIRS, model_name: str = "unknown",
    ) -> None:
        self._model, self._sandbox, self._settings = model, sandbox, settings
        self._max_repairs, self._model_name = max_repairs, model_name

    def solve(self, task: Task) -> SystemOutput:
        start = time.monotonic()
        text = task_prompt(task)
        resp = self._model.invoke(CODER_SYSTEM, BASELINE_USER.format(task=text))
        usage = resp.usage
        files = split_files(resp.text)[0]
        first_files, attempts = dict(files), 1
        had_error, first_ok, last_ok = False, None, False
        while True:
            _, result = execute_files(files, self._sandbox, self._settings)
            last_ok = not _failed(result)
            if first_ok is None:
                first_ok = last_ok
            had_error = had_error or not last_ok
            if last_ok or attempts > self._max_repairs:
                break
            stdout, stderr = exec_streams(result)
            resp = self._model.invoke(DEBUGGER_SYSTEM, BASELINE_REPAIR_USER.format(
                task=text, files=format_files(files), exec_summary=exec_summary(result),
                stdout=stdout, stderr=stderr,
            ))
            usage += resp.usage
            files = split_files(resp.text)[0]
            attempts += 1
        return SystemOutput(
            files=files, attempts=attempts, first_try_pass=first_ok, had_runtime_error=had_error,
            fixed=had_error and last_ok, usage=usage,
            cost_usd=cost_usd(self._model_name, usage), wall_s=time.monotonic() - start,
            first_files=first_files,
        )

    def describe(self) -> dict[str, Any]:
        return {
            "models": {"model": self._model_name},
            "settings": {**settings_dict(self._settings), "max_repairs": self._max_repairs},
        }

