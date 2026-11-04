"""Grade agent output by running hidden tests in a fresh sandboxed workspace.

Defences against a forged pass: agent files that could steer pytest are rejected,
pytest runs with config and conftest loading disabled, and a pass needs a parsed
summary showing at least one passed test and no failures or errors.

Remaining limit: agent code and tests share one process, so code that prints a fake
pytest summary and then exits 0 could still forge a pass. The grader is built for
LLM-agent output, not for an adversary.
"""
import re
import shutil
from dataclasses import dataclass
from pathlib import PurePosixPath

from coding_agent.evaluation.task import Task
from coding_agent.sandbox import Sandbox, make_workspace, truncate, write_files

# The sandbox cwd is the workspace root, so `python -m pytest` puts it on sys.path.
PYTEST_COMMAND = [
    "python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
    "--noconftest", "-c", "/dev/null", "--rootdir=.",
]
PROTECTED_NAMES = frozenset({
    "conftest.py", "pytest.ini", "setup.cfg", "tox.ini", "pyproject.toml",
    "sitecustomize.py", "usercustomize.py", "pytest.py",
})
_SUMMARY_COUNT = re.compile(r"(\d+) (passed|failed|errors?)\b")


@dataclass(frozen=True)
class GradeResult:
    """Whether the hidden tests passed, plus (truncated) pytest output."""

    passed: bool
    output: str


def protected_paths(files: dict[str, str]) -> list[str]:
    """Agent file paths that could change how pytest runs or shadow it."""
    return sorted(
        rel for rel in files
        if PurePosixPath(rel.lower()).name in PROTECTED_NAMES
        or "pytest" in PurePosixPath(rel.lower()).parts
    )


def _summary_shows_pass(output: str) -> bool:
    """True if the final summary line has >= 1 passed and no failed/error counts."""
    lines = [ln for ln in output.strip().splitlines() if " in " in ln]
    if not lines:
        return False
    counts: dict[str, int] = {}
    for n, kind in _SUMMARY_COUNT.findall(lines[-1]):
        counts[kind.rstrip("s") if kind.startswith("error") else kind] = int(n)
    return counts.get("passed", 0) >= 1 and not counts.get("failed") and not counts.get("error")


def grade(task: Task, files: dict[str, str], sandbox: Sandbox) -> GradeResult:
    """Run the task's hidden tests against the agent's files.

    Hidden tests are written last so an agent cannot overwrite them to fake a pass.
    """
    blocked = protected_paths(files)
    if blocked:
        return GradeResult(
            passed=False,
            output=f"rejected: protected file(s) not allowed: {', '.join(blocked)}",
        )
    workspace = make_workspace()
    try:
        write_files(workspace, files)
        write_files(workspace, task.fixtures)
        write_files(workspace, task.hidden_tests)
        result = sandbox.run(workspace, PYTEST_COMMAND)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
    output = result.stdout + result.stderr
    passed = result.exit_code == 0 and not result.timed_out and _summary_shows_pass(output)
    return GradeResult(passed=passed, output=truncate(output))
