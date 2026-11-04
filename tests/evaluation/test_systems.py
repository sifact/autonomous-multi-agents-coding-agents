"""Eval systems with FakeLLM. Execution is scripted (no Docker) except where noted."""
import pytest

from coding_agent.config import Settings
from coding_agent.evaluation import (
    GraphSystem,
    SingleAgentLoop,
    SingleShot,
    SystemOutput,
    load_tasks,
)
from coding_agent.llm import FakeLLM, ModelRouter, UsageTracker
from coding_agent.sandbox import ExecResult
from tests.graph.fakes import code, layout, plan, scripted_router, verdict

from .helpers import TASKS

BY_ID = {t.id: t for t in load_tasks(TASKS)}
SUM_CSV = BY_ID["sum_csv"]
FIX_MEAN = BY_ID["fix_mean"]


def files_reply(body: str, path: str = "main.py") -> str:
    return f"### FILE: {path}\n```python\n{body}\n```\n"


def res(exit_code=0, stderr=""):
    return ExecResult(exit_code, "", stderr, False, False, 0.1)


class ScriptedSandbox:
    """Hands out queued ExecResults; counts runs."""

    def __init__(self, *results):
        self.results, self.runs = list(results), 0

    def run(self, workspace, command, limits=None):
        self.runs += 1
        return self.results.pop(0)


class ForbiddenSandbox:
    def run(self, workspace, command, limits=None):
        pytest.fail("this system must never execute code")


@pytest.fixture
def settings():
    return Settings()


# --- SingleShot -------------------------------------------------------------


def test_single_shot_one_call_never_executes(settings):
    llm = FakeLLM([files_reply("print('ok')")])
    out = SingleShot(llm, ForbiddenSandbox(), model_name="m").solve(SUM_CSV)
    assert len(llm.calls) == 1
    assert out.files == {"main.py": "print('ok')\n"}
    assert out.first_files == out.files
    assert out.attempts == 1 and out.first_try_pass is None
    assert out.had_runtime_error is False and out.fixed is False
    assert out.usage.tokens_in > 0 and out.error is None
    assert out.cost_usd is None  # "m" has no price


def test_single_shot_unparseable_reply_gives_no_files():
    out = SingleShot(FakeLLM(["sorry, no code"]), ForbiddenSandbox()).solve(SUM_CSV)
    assert out.files == {}


def test_task_prompt_reaches_model_with_starter_and_fixture_listing():
    llm = FakeLLM([files_reply("x = 1")])
    SingleShot(llm, ForbiddenSandbox()).solve(FIX_MEAN)
    _, user = llm.calls[0]
    assert "mean" in user and "stats.py" in user  # prompt + starter file
    llm = FakeLLM([files_reply("x = 1")])
    SingleShot(llm, ForbiddenSandbox()).solve(SUM_CSV)
    assert "data.csv" in llm.calls[0][1]


# --- SingleAgentLoop --------------------------------------------------------


def test_loop_stops_after_first_success(settings):
    llm = FakeLLM([files_reply("print('ok')")])
    sb = ScriptedSandbox(res(0))
    out = SingleAgentLoop(llm, sb, settings).solve(SUM_CSV)
    assert len(llm.calls) == 1 and sb.runs == 1
    assert (out.attempts, out.first_try_pass, out.had_runtime_error, out.fixed) == (1, True, False, False)


def test_loop_repairs_with_stderr_then_stops(settings):
    llm = FakeLLM([files_reply("1/0"), files_reply("print('ok')")])
    sb = ScriptedSandbox(res(1, "ZeroDivisionError: division by zero"), res(0))
    out = SingleAgentLoop(llm, sb, settings).solve(SUM_CSV)
    assert len(llm.calls) == 2 and sb.runs == 2
    assert "ZeroDivisionError" in llm.calls[1][1]  # real stderr fed back
    assert (out.attempts, out.first_try_pass, out.had_runtime_error, out.fixed) == (2, False, True, True)
    assert out.first_files == {"main.py": "1/0\n"} and out.files == {"main.py": "print('ok')\n"}


def test_loop_stops_after_exactly_three_repairs(settings):
    llm = FakeLLM([files_reply(f"raise ValueError({i})") for i in range(6)])
    sb = ScriptedSandbox(*[res(1, f"ValueError: {i}") for i in range(6)])
    out = SingleAgentLoop(llm, sb, settings).solve(SUM_CSV)
    assert len(llm.calls) == 4 and sb.runs == 4  # 1 generation + 3 repairs
    assert (out.attempts, out.first_try_pass, out.had_runtime_error, out.fixed) == (4, False, True, False)
    assert out.files == {"main.py": "raise ValueError(3)\n"}


def test_loop_stderr_is_truncated(settings):
    llm = FakeLLM([files_reply("x"), files_reply("y")])
    sb = ScriptedSandbox(res(1, "E" * 100_000), res(0))
    SingleAgentLoop(llm, sb, settings).solve(SUM_CSV)
    assert len(llm.calls[1][1]) < 30_000


def test_loop_empty_reply_is_fed_back_not_crashed(settings):
    llm = FakeLLM(["no files here", files_reply("print('ok')")])
    sb = ScriptedSandbox(res(0))  # only the second attempt reaches the sandbox
    out = SingleAgentLoop(llm, sb, settings).solve(SUM_CSV)
    assert out.attempts == 2 and out.had_runtime_error and out.fixed
    assert "no files" in llm.calls[1][1].lower()


# --- GraphSystem ------------------------------------------------------------


def _graph_system(settings, sandbox, trackers, scripts):
    def factory(tracker):
        trackers.append(tracker)
        router, _ = scripted_router(settings, tracker, **scripts())
        return router

    return GraphSystem(factory, sandbox, settings)


def _happy_scripts():
    return {"planner": [plan()], "architect": [layout()], "coder": [code("print('ok')")],
            "reviewer": [verdict("pass")]}


def test_graph_system_output_and_fresh_tracker_per_task(settings):
    trackers: list[UsageTracker] = []
    sb = ScriptedSandbox(res(0), res(0))
    system = _graph_system(settings, sb, trackers, _happy_scripts)
    a, b = system.solve(SUM_CSV), system.solve(FIX_MEAN)
    assert len(trackers) == 2 and trackers[0] is not trackers[1]
    # Per-run usage: each output matches its own tracker, not a running total.
    assert a.usage.total > 0 and a.usage.total == trackers[0].total_tokens
    assert b.usage.total == trackers[1].total_tokens
    assert a.cost_usd is None  # fake models are unpriced
    assert (a.attempts, a.first_try_pass, a.had_runtime_error, a.fixed) == (1, True, False, False)
    assert a.files == {"main.py": "print('ok')\n"} and a.first_files == a.files


def test_graph_system_repair_run_flags(settings):
    trackers: list[UsageTracker] = []
    sb = ScriptedSandbox(res(1, "boom"), res(0))
    scripts = lambda: {
        "planner": [plan()], "architect": [layout()], "coder": [code("1/0")],
        "debugger": [code("print('ok')")], "reviewer": [verdict("fix"), verdict("pass")],
    }
    out = _graph_system(settings, sb, trackers, scripts).solve(SUM_CSV)
    assert (out.attempts, out.first_try_pass, out.had_runtime_error, out.fixed) == (2, False, True, True)
    assert out.first_files == {"main.py": "1/0\n"} and out.files == {"main.py": "print('ok')\n"}


def test_describe_lists_models_and_settings(settings):
    d = GraphSystem(lambda t: ModelRouter(settings, t, factory=lambda n: FakeLLM([])),
                    ForbiddenSandbox(), settings).describe()
    assert d["models"] == {"cheap": settings.model_cheap, "strong": settings.model_strong}
    assert d["settings"]["max_repairs"] == settings.max_repairs
    assert SingleAgentLoop(FakeLLM([]), ForbiddenSandbox(), settings, model_name="x").describe()["models"] == {"model": "x"}


def test_system_output_defaults():
    from coding_agent.llm import Usage
    out = SystemOutput({}, 1, None, False, False, Usage(0, 0), None, 0.0)
    assert out.error is None and out.first_files is None
