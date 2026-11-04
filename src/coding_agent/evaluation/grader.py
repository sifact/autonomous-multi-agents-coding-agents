"""Grade agent output by running hidden tests in a fresh sandboxed workspace."""
import shutil
from dataclasses import dataclass

from coding_agent.evaluation.task import Task
from coding_agent.sandbox import Sandbox, make_workspace, truncate, write_files

PYTEST_COMMAND = ["pytest", "-q"]


@dataclass(frozen=True)
class GradeResult:
    """Whether the hidden tests passed, plus (truncated) pytest output."""

    passed: bool
    output: str


def grade(task: Task, files: dict[str, str], sandbox: Sandbox) -> GradeResult:
    """Run the task's hidden tests against the agent's files.

    Hidden tests are written last so an agent cannot overwrite them to fake a pass.
    """
    workspace = make_workspace()
    try:
        write_files(workspace, files)
        write_files(workspace, task.fixtures)
        write_files(workspace, task.hidden_tests)
        result = sandbox.run(workspace, PYTEST_COMMAND)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
    passed = result.exit_code == 0 and not result.timed_out
    return GradeResult(passed=passed, output=truncate(result.stdout + result.stderr))
