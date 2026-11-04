from dataclasses import replace

import pytest

from coding_agent.evaluation import Task, grade, load_tasks, validate_all, validate_task
from coding_agent.sandbox import DockerSandbox, ExecResult
from tests.evaluation.helpers import TASKS

IMAGE = "coding-agent-sandbox:latest"
GOOD_TESTS = (
    "def test_a():\n    assert 1\n\ndef test_b():\n    assert 1\n\ndef test_c():\n    assert 1\n"
)


class FakeSandbox:
    """Passes when the workspace holds solution.py, fails otherwise."""

    def run(self, workspace, command, limits=None):
        ok = (workspace / "solution.py").exists()
        out = "3 passed in 0.01s\n" if ok else "3 failed in 0.01s\n"
        return ExecResult(0 if ok else 1, out, "", False, False, 0.1)


def make(**kw) -> Task:
    base = Task(
        id="t1", category="data_script", prompt="Write solution.py.", fixtures={},
        hidden_tests={"tests/test_hidden.py": GOOD_TESTS}, starter=None,
        reference={"solution.py": "x = 1"},
    )
    return replace(base, **kw)


def test_valid_task_has_no_problems():
    assert validate_task(make(), FakeSandbox()) == []


def test_empty_prompt_and_bad_category():
    problems = validate_task(make(prompt="  ", category="nope"), FakeSandbox())
    assert any("prompt" in p for p in problems)
    assert any("category" in p for p in problems)


def test_reference_failing_is_reported():
    problems = validate_task(make(reference={"other.py": "x"}), FakeSandbox())
    assert any("reference fails" in p for p in problems)


def test_missing_reference_is_reported():
    assert any("reference is empty" in p for p in validate_task(make(reference={}), FakeSandbox()))


def test_empty_passing_is_reported():
    class AlwaysPass:
        def run(self, workspace, command, limits=None):
            return ExecResult(0, "3 passed in 0.01s\n", "", False, False, 0.1)

    assert any("empty file set" in p for p in validate_task(make(), AlwaysPass()))


def test_starter_that_passes_is_reported():
    task = make(starter={"solution.py": "x = 0"})
    assert any("starter" in p for p in validate_task(task, FakeSandbox()))


def test_prompt_leaking_hidden_test_name():
    task = make(prompt="Make test_hidden.py pass.")
    assert any("hidden tests" in p for p in validate_task(task, FakeSandbox()))


def test_weak_hidden_tests_rejected():
    task = make(hidden_tests={"tests/test_hidden.py": "def test_a():\n    assert 1\n"})
    assert any("case" in p for p in validate_task(task, FakeSandbox()))


def test_parametrize_cases_are_counted():
    src = (
        "import pytest\n@pytest.mark.parametrize('x', [1, 2, 3])\n"
        "def test_a(x):\n    assert x\n"
    )
    assert validate_task(make(hidden_tests={"tests/test_hidden.py": src}), FakeSandbox()) == []


def test_validate_all_flags_duplicate_ids():
    report = validate_all([make(), make()], FakeSandbox())
    assert report["t1"] and "duplicate" in report["t1"][0]


@pytest.mark.docker
def test_sample_tasks_in_docker():
    by_id = {t.id: t for t in load_tasks(TASKS)}
    sb = DockerSandbox(IMAGE)
    # fix_mean has one test function only, so the only problem allowed is "too few cases".
    for task in by_id.values():
        problems = validate_task(task, sb)
        assert all("case(s)" in p for p in problems), problems
    assert grade(by_id["sum_csv"], by_id["sum_csv"].reference, sb).passed
