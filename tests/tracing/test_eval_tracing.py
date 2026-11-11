"""One trace per benchmark task run, grouped into a session named after the result file."""
import json

from coding_agent.evaluation import GraphSystem, SingleShot, run_benchmark
from coding_agent.llm import FakeLLM
from coding_agent.tracing import flush, langfuse_setup
from tests.evaluation.test_runner import TASK_LIST, FakeSystem, MarkerGrader, output
from tests.graph.fakes import CannedSandbox, code, layout, plan, scripted_router, verdict

OK_FILES = {"solution.py": "GOOD"}


def roots(memory):
    flush()
    return [s for s in memory.get_finished_spans() if s.parent is None]


def test_off_by_default_runs_exactly_as_before(tmp_path):
    records = run_benchmark(TASK_LIST, FakeSystem(output(OK_FILES), output(OK_FILES)),
                            MarkerGrader(), out_dir=tmp_path)
    assert [r.final_pass for r in records] == [True, True]


def test_one_trace_per_task_with_session_tags_and_scores(keyed, memory, tmp_path, monkeypatch):
    sent = []
    system = FakeSystem(output(OK_FILES), output({"solution.py": "bad"}))
    real_get = langfuse_setup.get_client

    def get_with_spy(settings):
        client = real_get(settings)
        if client is not None and not getattr(client, "_spied", False):
            client.create_score = lambda **kw: sent.append(kw)
            client._spied = True
        return client

    monkeypatch.setattr(langfuse_setup, "get_client", get_with_spy)
    run_benchmark(TASK_LIST, system, MarkerGrader(), out_dir=tmp_path, tracing=keyed)
    result_file = next(tmp_path.glob("fake-*.json"))
    found = roots(memory)
    assert len(found) == 2
    assert {r.name for r in found} == {"coding-agent/fake"}
    assert {r.attributes["session.id"] for r in found} == {result_file.stem}
    tags = [set(r.attributes["langfuse.trace.tags"]) for r in found]
    assert tags[0] >= {"fake", "fix_mean"} and len(tags[0]) == 3  # + the category
    assert tags[1] >= {"fake", "sum_csv"}
    outs = [json.loads(r.attributes["langfuse.observation.output"]) for r in found]
    assert [o["final_pass"] for o in outs] == [True, False]
    by_trace = {}
    for s in sent:
        by_trace.setdefault(s["trace_id"], {})[s["name"]] = s["value"]
    assert len(by_trace) == 2
    assert sorted(v["final_pass"] for v in by_trace.values()) == [0.0, 1.0]
    assert all({"first_try_pass", "matched_budget_pass"} <= set(v) for v in by_trace.values())


def test_crashed_task_trace_carries_the_error(keyed, memory, tmp_path):
    run_benchmark(TASK_LIST[:1], FakeSystem(RuntimeError("model blew up")), MarkerGrader(),
                  out_dir=tmp_path, tracing=keyed)
    (root,) = roots(memory)
    assert root.attributes["langfuse.observation.level"] == "ERROR"
    assert "model blew up" in root.attributes["langfuse.observation.status_message"]


def test_graph_system_nodes_land_in_the_task_trace_without_changing_the_system(
        keyed, memory, tmp_path):
    settings = keyed.model_copy(update={"workspace_root": tmp_path})

    def factory(tracker):
        return scripted_router(
            settings, tracker, planner=[plan()], architect=[layout()],
            coder=[code("print('GOOD')")], reviewer=[verdict("pass")])[0]

    from coding_agent.sandbox import ExecResult
    sandbox = CannedSandbox(ExecResult(0, "ok\n", "", False, False, 0.1))
    system = GraphSystem(factory, sandbox, settings)
    run_benchmark(TASK_LIST[:1], system, MarkerGrader(), out_dir=tmp_path, tracing=keyed)
    flush()
    spans = memory.get_finished_spans()
    assert len({s.context.trace_id for s in spans}) == 1
    assert {"planner", "architect", "coder", "executor", "reviewer", "finalize"} <= {
        s.name for s in spans}


def test_baseline_system_runs_inside_the_trace(keyed, memory, tmp_path):
    model = FakeLLM(["### FILE: solution.py\n```python\nGOOD\n```\n"])
    system = SingleShot(model, MarkerGrader(), model_name="fake")
    (rec,) = run_benchmark(TASK_LIST[:1], system, MarkerGrader(), out_dir=tmp_path,
                           tracing=keyed)
    assert rec.error is None
    assert [r.name for r in roots(memory)] == ["coding-agent/single_shot"]


def test_crashed_runs_get_no_quality_scores(keyed, memory, tmp_path):
    run_benchmark(TASK_LIST[:1], FakeSystem(RuntimeError("down")), MarkerGrader(),
                  out_dir=tmp_path, tracing=keyed)
    assert memory.scores == []


def test_graded_runs_do_get_scores(keyed, memory, tmp_path):
    run_benchmark(TASK_LIST[:1], FakeSystem(output(OK_FILES)), MarkerGrader(),
                  out_dir=tmp_path, tracing=keyed)
    assert {s["name"] for s in memory.scores} == {
        "final_pass", "first_try_pass", "matched_budget_pass"}
