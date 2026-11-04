"""Benchmark runner: fake systems + a content-based fake grader sandbox; one Docker end-to-end."""
import json
import random

import pytest

from coding_agent.config import Settings
from coding_agent.evaluation import (
    RunRecord,
    SingleAgentLoop,
    SystemOutput,
    load_tasks,
    run_benchmark,
)
from coding_agent.evaluation import runner as runner_mod
from coding_agent.llm import FakeLLM, Usage
from coding_agent.sandbox import DockerSandbox, ExecResult

from .helpers import TASKS

BY_ID = {t.id: t for t in load_tasks(TASKS)}
TASK_LIST = [BY_ID["fix_mean"], BY_ID["sum_csv"]]
IMAGE = "coding-agent-sandbox:latest"


class MarkerGrader:
    """Fake sandbox: hidden tests 'pass' iff any workspace .py file contains GOOD."""

    def __init__(self):
        self.runs = 0

    def run(self, workspace, command, limits=None):
        self.runs += 1
        good = any("GOOD" in p.read_text() for p in workspace.rglob("*.py"))
        out = "1 passed in 0.01s\n" if good else "1 failed in 0.01s\n"
        return ExecResult(0 if good else 1, out, "", False, False, 0.1)


def output(files, first_files=None, **kw):
    base = {"attempts": 1, "first_try_pass": None, "had_runtime_error": False, "fixed": False,
            "usage": Usage(10, 5), "cost_usd": None, "wall_s": 0.5}
    return SystemOutput(files=files, first_files=files if first_files is None else first_files,
                        **{**base, **kw})


class FakeSystem:
    name = "fake"

    def __init__(self, *steps):
        self.steps, self.seen = list(steps), []

    def solve(self, task):
        self.seen.append(task.id)
        step = self.steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return step

    def describe(self):
        return {"models": {"cheap": "c-model", "strong": "s-model"}, "settings": {"max_repairs": 3}}


def run(system, tmp_path, tasks=TASK_LIST, **kw):
    records = run_benchmark(tasks, system, MarkerGrader(), out_dir=tmp_path, **kw)
    return records


def test_first_try_graded_from_first_files_not_final(tmp_path):
    sysm = FakeSystem(
        output({"solution.py": "GOOD"}, first_files={"solution.py": "bad"}, attempts=2,
               first_try_pass=False, had_runtime_error=True, fixed=True),
        output({"solution.py": "GOOD"}),
    )
    a, b = run(sysm, tmp_path)
    assert (a.first_try_pass, a.final_pass, a.fixed_within_3, a.attempts) == (False, True, True, 2)
    assert (b.first_try_pass, b.final_pass) == (True, True)  # single try: reuses the one grade
    assert a.tokens_in == 10 and a.tokens_out == 5 and a.cost_usd is None and a.error is None


def test_identical_first_and_final_files_graded_once(tmp_path):
    grader = MarkerGrader()
    run_benchmark(TASK_LIST[:1], FakeSystem(output({"solution.py": "GOOD"})), grader, out_dir=tmp_path)
    assert grader.runs == 1


def test_exception_becomes_failed_record_and_run_continues(tmp_path):
    sysm = FakeSystem(RuntimeError("model blew up"), output({"solution.py": "GOOD"}))
    a, b = run(sysm, tmp_path)
    assert a.error == "RuntimeError: model blew up"
    assert not a.first_try_pass and not a.final_pass and a.attempts == 0 and a.cost_usd is None
    assert b.final_pass and b.error is None
    assert sysm.seen == ["fix_mean", "sum_csv"]


def test_three_consecutive_failures_reraise_but_results_are_saved(tmp_path):
    sysm = FakeSystem(*[OSError("docker down")] * 3)
    with pytest.raises(OSError, match="docker down"):
        run_benchmark(TASK_LIST * 2, sysm, MarkerGrader(), out_dir=tmp_path)
    saved = json.loads(next(tmp_path.glob("fake-*.json")).read_text())
    assert len(saved["records"]) == 3 and saved["records"][0]["error"]


def test_success_resets_consecutive_failure_count(tmp_path):
    ok = output({"solution.py": "GOOD"})
    sysm = FakeSystem(OSError("x"), OSError("x"), ok, OSError("x"), OSError("x"), ok)
    records = run(sysm, tmp_path, tasks=TASK_LIST * 3)
    assert len(records) == 6


def test_repeats_and_on_record(tmp_path):
    ok = output({"solution.py": "GOOD"})
    seen: list[RunRecord] = []
    records = run(FakeSystem(ok, ok, ok, ok), tmp_path, repeats=2, on_record=seen.append)
    assert len(records) == 4 and seen == records


def test_seed_is_applied_before_each_run(tmp_path):
    draws = []

    class Probe(FakeSystem):
        def solve(self, task):
            draws.append(random.random())
            return super().solve(task)

    ok = output({"solution.py": "GOOD"})
    run(Probe(ok, ok), tmp_path, seed=7)
    random.seed(7)
    expected = random.random()
    assert draws == [expected, expected]


def test_max_rpm_spaces_run_starts(tmp_path, monkeypatch):
    sleeps = []
    monkeypatch.setattr(runner_mod, "_sleep", sleeps.append)
    ok = output({"solution.py": "GOOD"})
    run(FakeSystem(ok, ok), tmp_path, max_rpm=30)
    assert len(sleeps) == 1 and 0 < sleeps[0] <= 2.0  # 60/30 s minus elapsed


def test_result_json_round_trips(tmp_path):
    ok = output({"solution.py": "GOOD"})
    records = run(FakeSystem(ok, ok), tmp_path, seed=3, repeats=1)
    files = list(tmp_path.glob("fake-*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text())
    assert data["system"] == "fake" and data["seed"] == 3 and data["repeats"] == 1
    assert data["models"] == {"cheap": "c-model", "strong": "s-model"}
    assert data["settings"]["max_repairs"] == 3
    assert "git_sha" in data and "timestamp" in data
    assert data["task_ids"] == ["fix_mean", "sum_csv"]
    assert [RunRecord(**r) for r in data["records"]] == records
    assert data["records"][0]["cost_usd"] is None  # unpriced stays null, not 0
    m = data["metrics"]
    assert m["n"] == 2 and m["mean_cost_usd"] is None and m["cost_known"] is False
    assert m["cost_known_count"] == 0 and m["runtime_errors_fixed_pct"] is None


def test_git_sha_tolerates_absence(monkeypatch):
    monkeypatch.setattr(runner_mod.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError()))
    assert runner_mod.git_sha() is None


@pytest.mark.docker
def test_first_try_pass_from_first_execution_real_grading(tmp_path):
    """Buggy first attempt (crashes + wrong), fixed second: real sandbox and hidden tests."""
    settings = Settings(sandbox_image=IMAGE)
    ref = BY_ID["sum_csv"].reference["solution.py"]
    buggy = (
        "### FILE: solution.py\n```python\ndef total(path):\n    return 0.0\n```\n"
        "### FILE: main.py\n```python\nraise RuntimeError('first attempt crashes')\n```\n"
    )
    fixed = (
        f"### FILE: solution.py\n```python\n{ref}\n```\n"
        "### FILE: main.py\n```python\nimport solution\nprint('ok')\n```\n"
    )
    sandbox = DockerSandbox(IMAGE)
    system = SingleAgentLoop(FakeLLM([buggy, fixed]), sandbox, settings, model_name="fake")
    (rec,) = run_benchmark([BY_ID["sum_csv"]], system, sandbox, out_dir=tmp_path)
    assert rec.first_try_pass is False and rec.final_pass is True
    assert rec.had_runtime_error and rec.fixed_within_3 and rec.attempts == 2
    assert rec.cost_usd is None and rec.error is None
