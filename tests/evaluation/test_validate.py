from dataclasses import replace

import pytest

from coding_agent.evaluation import Task, grade, load_tasks, validate_all, validate_task
from coding_agent.evaluation.validate import count_test_cases
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


def test_tests_without_checks_do_not_count():
    src = "def test_a():\n    pass\n\ndef test_b():\n    pass\n\ndef test_c():\n    pass\n"
    assert count_test_cases(src) == 0
    assert any("case" in p for p in validate_task(make(hidden_tests={"t.py": src}), FakeSandbox()))


def test_raises_and_approx_count_as_checks():
    src = (
        "import pytest\n"
        "def test_a():\n    with pytest.raises(ValueError):\n        int('x')\n"
        "def test_b():\n    x = 1.0 == pytest.approx(1.0)\n"
    )
    assert count_test_cases(src) == 2


def test_only_collectible_tests_count():
    src = (
        "def helper_test():\n    assert 1\n"
        "def _test_x():\n    assert 1\n"
        "def test_top():\n    assert 1\n"
        "class Helper:\n    def test_m(self):\n        assert 1\n"
        "class TestGroup:\n    def test_m(self):\n        assert 1\n"
        "    def other(self):\n        assert 1\n"
        "def outer():\n    def test_nested():\n        assert 1\n"
    )
    assert count_test_cases(src) == 2


def test_prompt_leaking_test_function_name():
    tests = GOOD_TESTS.replace("test_b", "test_total_by_month")
    task = make(hidden_tests={"tests/test_hidden.py": tests}, prompt="See test_total_by_month.")
    assert any("test_total_by_month" in p for p in validate_task(task, FakeSandbox()))
    ok = make(hidden_tests={"tests/test_hidden.py": tests}, prompt="Compute totals by month.")
    assert validate_task(ok, FakeSandbox()) == []


def test_difficulty_validation():
    assert validate_task(make(difficulty="easy"), FakeSandbox(), require_difficulty=True) == []
    assert validate_task(make(), FakeSandbox()) == []  # optional by default
    missing = validate_task(make(), FakeSandbox(), require_difficulty=True)
    assert any("missing difficulty" in p for p in missing)
    bad = validate_task(make(difficulty="x"), FakeSandbox())
    assert any("invalid difficulty" in p for p in bad)


def test_validate_all_passes_require_difficulty():
    report = validate_all([make()], FakeSandbox(), require_difficulty=True)
    assert any("difficulty" in p for p in report["t1"])


@pytest.mark.docker
def test_sample_tasks_in_docker():
    by_id = {t.id: t for t in load_tasks(TASKS)}
    sb = DockerSandbox(IMAGE)
    # Samples are deliberately small: the only expected problem is too few hidden cases.
    expected = {
        "fix_mean": ["hidden tests have 1 case(s); need at least 3"],
        "sum_csv": ["hidden tests have 2 case(s); need at least 3"],
    }
    assert {i: validate_task(t, sb) for i, t in by_id.items()} == expected
    assert grade(by_id["sum_csv"], by_id["sum_csv"].reference, sb).passed
