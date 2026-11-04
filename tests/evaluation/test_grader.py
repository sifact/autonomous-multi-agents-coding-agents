from pathlib import Path

import pytest

from coding_agent.evaluation import grade, load_tasks
from coding_agent.evaluation.grader import PYTEST_COMMAND
from coding_agent.sandbox import DockerSandbox, ExecResult

IMAGE = "coding-agent-sandbox:latest"
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


PASS_OUT = "1 passed in 0.01s\n"


def _res(exit_code=0, timed_out=False, stdout=PASS_OUT):
    return ExecResult(exit_code, stdout, "", timed_out, False, 0.1)


def test_grade_writes_everything_and_cleans_up():
    task = BY_ID["sum_csv"]
    sb = RecordingSandbox(_res())
    result = grade(task, {"solution.py": "x = 1"}, sb)
    assert result.passed and result.output == PASS_OUT
    assert sb.command == PYTEST_COMMAND
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


def test_exit_zero_without_summary_is_not_a_pass():
    assert not grade(BY_ID["sum_csv"], {}, RecordingSandbox(_res(0, stdout=""))).passed


def test_zero_tests_collected_is_not_a_pass():
    out = "no tests ran in 0.00s\n"
    assert not grade(BY_ID["sum_csv"], {}, RecordingSandbox(_res(0, stdout=out))).passed


def test_failed_in_summary_is_not_a_pass_even_with_exit_zero():
    out = "1 failed, 2 passed in 0.01s\n"
    assert not grade(BY_ID["sum_csv"], {}, RecordingSandbox(_res(0, stdout=out))).passed


def test_passed_with_warnings_and_skips_is_a_pass():
    out = "3 passed, 1 skipped, 2 warnings in 0.05s\n"
    assert grade(BY_ID["sum_csv"], {}, RecordingSandbox(_res(0, stdout=out))).passed


@pytest.mark.parametrize(
    "name",
    ["conftest.py", "pytest.ini", "setup.cfg", "tox.ini", "pyproject.toml",
     "sitecustomize.py", "usercustomize.py", "pytest.py",
     "sub/conftest.py", "a/b/tox.ini", "pytest/x.py", "src/pytest/__init__.py"],
)
def test_protected_names_fail_without_running(name):
    sb = RecordingSandbox(_res())
    result = grade(BY_ID["sum_csv"], {"solution.py": "x = 1", name: "x"}, sb)
    assert not result.passed
    assert name in result.output and "protected" in result.output
    assert sb.command is None  # never ran


def test_cleanup_when_sandbox_raises():
    class Boom:
        workspace = None

        def run(self, workspace, command, limits=None):
            self.workspace = workspace
            raise RuntimeError("infra")

    sb = Boom()
    with pytest.raises(RuntimeError):
        grade(BY_ID["sum_csv"], {}, sb)
    assert not sb.workspace.exists()


@pytest.mark.docker
def test_os_exit_zero_solution_is_not_a_pass():
    task = BY_ID["sum_csv"]
    files = {"solution.py": "import os\nos._exit(0)\n"}
    assert not grade(task, files, DockerSandbox(IMAGE)).passed


@pytest.mark.docker
@pytest.mark.parametrize("name", ["conftest.py", "pytest.ini", "tox.ini"])
def test_forged_config_is_rejected_in_docker(name):
    task = BY_ID["fix_mean"]
    files = {**task.starter, name: "[pytest]\naddopts = -k nothing\n"}
    result = grade(task, files, DockerSandbox(IMAGE))
    assert not result.passed and name in result.output


@pytest.mark.docker
@pytest.mark.parametrize("task_id", sorted(BY_ID))
def test_reference_passes(task_id):
    task = BY_ID[task_id]
    result = grade(task, task.reference, DockerSandbox(IMAGE))
    assert result.passed, result.output


@pytest.mark.docker
def test_starter_and_empty_fail():
    sb = DockerSandbox(IMAGE)
    starter = grade(BY_ID["fix_mean"], BY_ID["fix_mean"].starter, sb)
    assert not starter.passed and "1 failed" in starter.output
    empty = grade(BY_ID["sum_csv"], {}, sb)
    assert not empty.passed and "ModuleNotFoundError" in empty.output


@pytest.mark.docker
def test_agent_cannot_fake_pass_with_own_hidden_test():
    task = BY_ID["fix_mean"]
    files = {**task.starter, "tests/test_hidden.py": "def test_x():\n    assert True\n"}
    assert not grade(task, files, DockerSandbox(IMAGE)).passed


@pytest.mark.docker
@pytest.mark.parametrize(
    "name,content",
    [
        (
            "conftest.py",
            "def pytest_collection_modifyitems(items):\n    items.clear()\n",
        ),
        ("pytest.ini", "[pytest]\naddopts = -k nothing_matches\n"),
        ("tox.ini", "[pytest]\naddopts = -k nothing_matches\n"),
    ],
)
def test_command_ignores_config_even_if_protected_check_is_bypassed(name, content):
    """Second layer: the pytest command itself must not load agent config."""
    from coding_agent.evaluation.grader import PYTEST_COMMAND
    from coding_agent.sandbox import make_workspace, write_files

    task = BY_ID["fix_mean"]
    ws = make_workspace()
    try:
        write_files(ws, {**task.reference, name: content})
        write_files(ws, task.hidden_tests)
        res = DockerSandbox(IMAGE).run(ws, PYTEST_COMMAND)
    finally:
        import shutil

        shutil.rmtree(ws, ignore_errors=True)
    assert res.exit_code == 0 and "1 passed" in res.stdout
