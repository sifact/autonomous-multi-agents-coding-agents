from pathlib import Path

import pytest

from coding_agent.evaluation import GradeResult, grade, load_tasks
from coding_agent.sandbox import DockerSandbox, ExecResult

TASKS = Path(__file__).parent.parent / "fixtures" / "tasks"
BY_ID = {t.id: t for t in load_tasks(TASKS)}


class RecordingSandbox:
    """Fake sandbox: records the workspace listing and returns a canned result."""

    def __init__(self, result: ExecResult):
        self.result = result
        self.seen: dict[str, str] = {}
        self.workspace: Path | None = None
        self.command: list[str] | None = None

    def run(self, workspace, command, limits=None):
        self.workspace = workspace
        self.command = command
        self.seen = {
            p.relative_to(workspace).as_posix(): p.read_text()
            for p in workspace.rglob("*")
            if p.is_file()
        }
        return self.result


def _res(exit_code=0, timed_out=False, stdout=""):
    return ExecResult(exit_code, stdout, "", timed_out, False, 0.1)


def test_grade_writes_everything_and_cleans_up():
    task = BY_ID["sum_csv"]
    sb = RecordingSandbox(_res())
    result = grade(task, {"solution.py": "x = 1"}, sb)
    assert result == GradeResult(passed=True, output="")
    assert sb.command == ["pytest", "-q"]
    assert {"solution.py", "data.csv", "tests/test_hidden.py"} <= sb.seen.keys()
    assert not sb.workspace.exists()


def test_nonzero_exit_fails():
    assert not grade(BY_ID["sum_csv"], {}, RecordingSandbox(_res(1, stdout="boom"))).passed


def test_timeout_fails_even_with_zero_exit():
    assert not grade(BY_ID["sum_csv"], {}, RecordingSandbox(_res(0, timed_out=True))).passed


def test_hidden_tests_override_agent_files():
    task = BY_ID["sum_csv"]
    fake = "def test_x():\n    assert True\n"
    sb = RecordingSandbox(_res())
    grade(task, {"tests/test_hidden.py": fake}, sb)
    assert sb.seen["tests/test_hidden.py"] == task.hidden_tests["tests/test_hidden.py"]


def test_output_is_truncated():
    out = grade(BY_ID["sum_csv"], {}, RecordingSandbox(_res(1, stdout="x" * 50_000))).output
    assert "truncated" in out and len(out) < 21_000


@pytest.mark.docker
@pytest.mark.parametrize("task_id", sorted(BY_ID))
def test_reference_passes(task_id):
    task = BY_ID[task_id]
    result = grade(task, task.reference, DockerSandbox("coding-agent-sandbox:latest"))
    assert result.passed, result.output


@pytest.mark.docker
def test_starter_and_empty_fail():
    sb = DockerSandbox("coding-agent-sandbox:latest")
    assert not grade(BY_ID["fix_mean"], BY_ID["fix_mean"].starter, sb).passed
    assert not grade(BY_ID["sum_csv"], {}, sb).passed


@pytest.mark.docker
def test_agent_cannot_fake_pass_with_own_hidden_test():
    task = BY_ID["fix_mean"]
    files = {**task.starter, "tests/test_hidden.py": "def test_x():\n    assert True\n"}
    assert not grade(task, files, DockerSandbox("coding-agent-sandbox:latest")).passed
