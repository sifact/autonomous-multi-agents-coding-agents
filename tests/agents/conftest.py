import json

import pytest

from coding_agent.graph import Step, Verdict, initial_state
from coding_agent.sandbox import ExecResult


def plan_json(n_steps: int = 2) -> str:
    steps = [{"id": i, "description": f"step {i}", "acceptance": f"check {i}"} for i in range(1, n_steps + 1)]
    return "```json\n" + json.dumps({"steps": steps, "criteria": ["prints ok"]}) + "\n```"


def ok_exec(stdout: str = "ok\n") -> ExecResult:
    return ExecResult(0, stdout, "", False, False, 0.1)


def failed_exec(stderr: str = "Traceback (most recent call last):\nZeroDivisionError: division by zero\n") -> ExecResult:
    return ExecResult(1, "", stderr, False, False, 0.1)


@pytest.fixture
def state():
    s = initial_state("Print ok")
    s["plan"] = [Step(id=1, description="print", acceptance="ok printed")]
    s["criteria"] = ["prints ok"]
    s["layout"] = ["main.py: entry point"]
    return s


@pytest.fixture
def reviewed_state(state):
    """State after one failed run and a `fix` verdict."""
    state["files"] = {"main.py": "print(1/0)"}
    state["last_exec"] = failed_exec()
    state["code_versions"] = [{"version": 1, "files": dict(state["files"]), "flags": []}]
    state["verdict"] = Verdict(action="fix", reason="divide by zero on line 1")
    state["visits"] = 5
    return state
