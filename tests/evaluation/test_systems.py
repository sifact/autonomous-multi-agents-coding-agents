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
from coding_agent.llm import FakeLLM, ModelRouter, ScriptExhaustedError, UsageTracker
from coding_agent.sandbox import ExecResult
from tests.graph.fakes import code, layout, plan, scripted_router, verdict

from .helpers import TASKS

BY_ID = {t.id: t for t in load_tasks(TASKS)}
SUM_CSV = BY_ID["sum_csv"]
FIX_MEAN = BY_ID["fix_mean"]


def files_reply(body: str, path: str = "main.py") -> str:
    return f"### FILE: {path}\n```python\n{body}\n```\n"


def flags(out):
    return (out.attempts, out.first_try_pass, out.had_runtime_error, out.fixed)


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
    out = SingleShot(FakeLLM(["sorry, no code"]), ForbiddenSandbox(), model_name="m").solve(SUM_CSV)
    assert out.files == {}


def test_task_prompt_reaches_model_with_starter_and_fixture_listing():
    llm = FakeLLM([files_reply("x = 1")])
    SingleShot(llm, ForbiddenSandbox(), model_name="m").solve(FIX_MEAN)
    _, user = llm.calls[0]
    assert "mean" in user and "stats.py" in user  # prompt + starter file
    llm = FakeLLM([files_reply("x = 1")])
    SingleShot(llm, ForbiddenSandbox(), model_name="m").solve(SUM_CSV)
    assert "data.csv" in llm.calls[0][1]


# --- SingleAgentLoop --------------------------------------------------------


def test_loop_stops_after_first_success(settings):
    llm = FakeLLM([files_reply("print('ok')")])
    sb = ScriptedSandbox(res(0))
    out = SingleAgentLoop(llm, sb, settings, model_name="m").solve(SUM_CSV)
    assert len(llm.calls) == 1 and sb.runs == 1
    assert flags(out) == (1, True, False, False)


def test_loop_repairs_with_stderr_then_stops(settings):
    llm = FakeLLM([files_reply("1/0"), files_reply("print('ok')")])
    sb = ScriptedSandbox(res(1, "ZeroDivisionError: division by zero"), res(0))
    out = SingleAgentLoop(llm, sb, settings, model_name="m").solve(SUM_CSV)
    assert len(llm.calls) == 2 and sb.runs == 2
    assert "ZeroDivisionError" in llm.calls[1][1]  # real stderr fed back
    assert flags(out) == (2, False, True, True)
    assert out.first_files == {"main.py": "1/0\n"} and out.files == {"main.py": "print('ok')\n"}


def test_loop_stops_after_exactly_three_repairs(settings):
    llm = FakeLLM([files_reply(f"raise ValueError({i})") for i in range(6)])
    sb = ScriptedSandbox(*[res(1, f"ValueError: {i}") for i in range(6)])
    out = SingleAgentLoop(llm, sb, settings, model_name="m").solve(SUM_CSV)
    assert len(llm.calls) == 4 and sb.runs == 4  # 1 generation + 3 repairs
    assert flags(out) == (4, False, True, False)
    assert out.files == {"main.py": "raise ValueError(3)\n"}


def test_loop_stderr_is_truncated(settings):
    llm = FakeLLM([files_reply("x"), files_reply("y")])
    sb = ScriptedSandbox(res(1, "E" * 100_000), res(0))
    SingleAgentLoop(llm, sb, settings, model_name="m").solve(SUM_CSV)
    assert len(llm.calls[1][1]) < 30_000


def test_loop_empty_reply_is_fed_back_not_crashed(settings):
    llm = FakeLLM(["no files here", files_reply("print('ok')")])
    sb = ScriptedSandbox(res(0))  # only the second attempt reaches the sandbox
    out = SingleAgentLoop(llm, sb, settings, model_name="m").solve(SUM_CSV)
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
    assert flags(out) == (2, False, True, True)
    assert out.first_files == {"main.py": "1/0\n"} and out.files == {"main.py": "print('ok')\n"}


def test_describe_lists_models_and_settings(settings):
    d = GraphSystem(lambda t: ModelRouter(settings, t, factory=lambda n: FakeLLM([])),
                    ForbiddenSandbox(), settings).describe()
    assert d["models"] == {"cheap": settings.model_cheap, "strong": settings.model_strong}
    assert d["settings"]["max_repairs"] == settings.max_repairs
    loop = SingleAgentLoop(FakeLLM([]), ForbiddenSandbox(), settings, model_name="x")
    assert loop.describe()["models"] == {"model": "x"}


def _variant_system(settings, variant, trackers, scripts):
    def factory(tracker):
        trackers.append(tracker)
        return scripted_router(settings, tracker, **scripts())[0]

    return GraphSystem(factory, ScriptedSandbox(res(0)), settings, variant=variant)


def test_graph_system_default_variant_is_full_and_described(settings):
    system = GraphSystem(lambda t: None, ForbiddenSandbox(), settings)
    assert system.variant == "full" and system.name == "graph"
    assert system.describe()["variant"] == "full"


def test_graph_system_rejects_an_unknown_variant(settings):
    with pytest.raises(ValueError, match="unknown graph variant"):
        GraphSystem(lambda t: None, ForbiddenSandbox(), settings, variant="no-coder")


def test_no_planner_variant_runs_without_a_planner_call(settings):
    scripts = lambda: {"architect": [layout()], "coder": [code("print('ok')")],
                       "reviewer": [verdict("pass")]}
    system = _variant_system(settings, "no-planner", [], scripts)
    out = system.solve(SUM_CSV)
    assert out.attempts == 1 and out.files == {"main.py": "print('ok')\n"}
    assert system.describe()["variant"] == "no-planner"


def test_no_architect_variant_runs_without_an_architect_call(settings):
    scripts = lambda: {"planner": [plan()], "coder": [code("print('ok')")],
                       "reviewer": [verdict("pass")]}
    out = _variant_system(settings, "no-architect", [], scripts).solve(SUM_CSV)
    assert out.attempts == 1 and out.files == {"main.py": "print('ok')\n"}


@pytest.mark.parametrize("variant,skipped,ran", [
    ("no-planner", "planner", "architect"), ("no-architect", "architect", "planner"),
])
def test_resolved_roles_mark_the_skipped_role(settings, variant, skipped, ran):
    scripts = lambda: {"planner": [plan()], "architect": [layout()],
                       "coder": [code("print('ok')")], "reviewer": [verdict("pass")]}
    system = _variant_system(settings, variant, [], scripts)
    system.solve(SUM_CSV)
    roles = system.describe()["resolved_roles"]
    assert roles[skipped] == "skipped" and roles[ran] == f"fake-{ran}"
    assert roles["coder"] == "fake-coder"


def test_full_variant_resolves_every_role_to_a_model(settings):
    scripts = lambda: {"planner": [plan()], "architect": [layout()],
                       "coder": [code("print('ok')")], "reviewer": [verdict("pass")]}
    system = _variant_system(settings, "full", [], scripts)
    system.solve(SUM_CSV)
    assert "skipped" not in system.describe()["resolved_roles"].values()


def test_system_output_defaults():
    from coding_agent.llm import Usage
    out = SystemOutput({}, 1, None, False, False, Usage(0, 0), None, 0.0)
    assert out.error is None and out.first_files is None


# --- partial usage on crash -------------------------------------------------


def test_single_shot_crash_carries_zero_partial_usage():
    with pytest.raises(ScriptExhaustedError) as ei:
        SingleShot(FakeLLM([]), ForbiddenSandbox(), model_name="m").solve(SUM_CSV)
    assert ei.value.partial_usage.total == 0 and ei.value.partial_wall_s >= 0


def test_loop_crash_carries_tokens_spent_so_far(settings):
    llm = FakeLLM([files_reply("1/0")])  # second call (the repair) exhausts the script
    sb = ScriptedSandbox(res(1, "boom"))
    with pytest.raises(ScriptExhaustedError) as ei:
        SingleAgentLoop(llm, sb, settings, model_name="m").solve(SUM_CSV)
    assert ei.value.partial_usage.total > 0
    assert ei.value.partial_cost_usd is None  # "m" is unpriced


def test_graph_crash_carries_tracker_usage(settings):
    trackers: list[UsageTracker] = []
    scripts = lambda: {"planner": [plan()], "architect": [layout()], "coder": []}
    system = _graph_system(settings, ScriptedSandbox(), trackers, scripts)
    with pytest.raises(ScriptExhaustedError) as ei:
        system.solve(SUM_CSV)
    assert ei.value.partial_usage.total == trackers[0].total_tokens > 0


# --- budgets ----------------------------------------------------------------


def test_budget_files_for_baselines_equal_final(settings):
    out = SingleShot(FakeLLM([files_reply("x")]), ForbiddenSandbox(), model_name="m").solve(SUM_CSV)
    assert out.budget_files == out.files
    llm = FakeLLM([files_reply(f"v{i}") for i in range(6)])
    sb = ScriptedSandbox(*[res(1, "e")] * 6)
    out = SingleAgentLoop(llm, sb, settings, model_name="m").solve(SUM_CSV)
    assert out.attempts == 4 and out.budget_files == out.files


def test_loop_default_repairs_come_from_settings():
    s = Settings(max_repairs=1)
    llm = FakeLLM([files_reply(f"v{i}") for i in range(6)])
    sb = ScriptedSandbox(*[res(1, "e")] * 6)
    out = SingleAgentLoop(llm, sb, s, model_name="m").solve(SUM_CSV)
    assert out.attempts == 2


def _gen6_scripts():
    """Replan after generation 2; the 6th generation is the first that contains GOOD."""
    bad = lambda i: code(f"print({i})")
    return {
        "planner": [plan("a"), plan("b")], "architect": [layout(), layout()],
        "coder": [bad(1), bad(3)],
        "debugger": [bad(2), bad(4), bad(5), code("print('GOOD')")],
        "reviewer": [verdict("fix"), verdict("replan"), verdict("fix"), verdict("fix"),
                     verdict("fix"), verdict("pass")],
    }


class GoodMarkerSandbox:
    """Exit 0 iff some workspace file contains GOOD (used for running and for grading)."""

    def run(self, workspace, command, limits=None):
        good = any("GOOD" in p.read_text() for p in workspace.rglob("*.py"))
        return ExecResult(0 if good else 1, "1 passed in 0.01s\n" if good else "1 failed\n",
                          "" if good else "boom", False, False, 0.0)


def test_graph_replan_then_pass_on_generation_six_misses_matched_budget(settings):
    from coding_agent.evaluation import run_benchmark
    system = _graph_system(settings, GoodMarkerSandbox(), [], _gen6_scripts)
    out = system.solve(SUM_CSV)
    assert out.attempts == 6 and "GOOD" in out.files["main.py"]
    assert "GOOD" not in out.budget_files["main.py"]  # generation 4 = max_repairs + 1
    assert out.had_runtime_error and not out.fixed  # 5 repairs-equivalents > 3
    import tempfile
    from pathlib import Path
    system = _graph_system(settings, GoodMarkerSandbox(), [], _gen6_scripts)
    with tempfile.TemporaryDirectory() as d:
        (r,) = run_benchmark([SUM_CSV], system, GoodMarkerSandbox(), out_dir=Path(d))
    assert r.final_pass is True and r.matched_budget_pass is False and r.first_try_pass is False


def test_graph_repair_limit_stop_uses_fourth_generation(settings):
    bads = [code(f"print({i})") for i in range(4)]
    scripts = lambda: {
        "planner": [plan()], "architect": [layout()], "coder": bads[:1], "debugger": bads[1:],
        "reviewer": [verdict("fix")] * 4,
    }
    out = _graph_system(settings, ScriptedSandbox(*[res(1, "e")] * 4), [], scripts).solve(SUM_CSV)
    assert out.attempts == 4 and out.budget_files == out.files and not out.fixed


def test_graph_describe_reports_resolved_roles(settings):
    system = _graph_system(settings, ScriptedSandbox(res(0)), [], _happy_scripts)
    assert "resolved_roles" not in system.describe() or system.describe()["resolved_roles"] == {}
    system.solve(SUM_CSV)
    assert system.describe()["resolved_roles"]["coder"] == "fake-coder"
