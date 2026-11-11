"""Callbacks must reach every node and the model call inside it (recording handler, offline)."""
from typing import TypedDict
from uuid import UUID

import pytest
from langchain_core.callbacks import BaseCallbackHandler
from langgraph.graph import END, START, StateGraph

from coding_agent.config import Settings
from coding_agent.graph import build_graph, run_graph, run_task, stream_task
from coding_agent.llm import GroqChatModel
from coding_agent.sandbox import ExecResult
from coding_agent.tracing import trace_run
from tests.graph.fakes import CannedSandbox, code, layout, plan, scripted_router, verdict

OK = ExecResult(0, "ok\n", "", False, False, 0.1)
NODES = ["planner", "architect", "coder", "executor", "reviewer", "finalize"]


class Recorder(BaseCallbackHandler):
    def __init__(self):
        self.chains: list[tuple[str, UUID, UUID | None]] = []
        self.models: list[tuple[str, UUID | None]] = []
        self.outputs: dict[str, dict] = {}
        self._names: dict[UUID, str] = {}

    def on_chain_start(self, serialized, inputs, *, run_id, parent_run_id=None, name=None, **kw):
        self._names[run_id] = name or ""
        self.chains.append((name or "", run_id, parent_run_id))

    def on_chain_end(self, outputs, *, run_id, **kw):
        self.outputs[self._names.get(run_id, "")] = outputs

    def on_chat_model_start(self, serialized, messages, *, run_id, parent_run_id=None, **kw):
        self.models.append((str(serialized.get("name") or serialized.get("id")), parent_run_id))

    def node_names(self):
        return [n for n, _, _ in self.chains]


def _graph(settings):
    router, _ = scripted_router(
        settings, planner=[plan()], architect=[layout()], coder=[code("print('ok')")],
        reviewer=[verdict("pass")])
    return build_graph(router, CannedSandbox(OK), settings)


@pytest.fixture
def settings(tmp_path):
    return Settings(workspace_root=tmp_path, _env_file=None)


@pytest.mark.parametrize("runner", ["run_graph", "run_task", "stream_task"])
def test_every_node_reports_to_the_handler_passed_as_config(settings, runner):
    rec = Recorder()
    config = {"callbacks": [rec], "metadata": {"langfuse_session_id": "s"}}
    graph = _graph(settings)
    if runner == "stream_task":
        list(stream_task(graph, "Print ok", config=config))
    elif runner == "run_task":
        run_task(graph, "Print ok", config=config)
    else:
        run_graph(graph, "Print ok", config=config)
    for node in NODES:
        assert node in rec.node_names(), (node, rec.node_names())


def test_node_outputs_are_visible_to_the_handler(settings):
    rec = Recorder()
    run_graph(_graph(settings), "Print ok", config={"callbacks": [rec]})
    assert "plan" in rec.outputs["planner"] and "code_versions" in rec.outputs["executor"]
    assert rec.outputs["finalize"]["final"].success


def test_without_config_nothing_changes(settings):
    assert run_task(_graph(settings), "Print ok").success


class _S(TypedDict, total=False):
    err: str


def _groq_node_graph(model, recorder):
    def node(state: _S) -> _S:
        try:
            model.invoke("sys", "hello")
        except Exception as exc:  # noqa: BLE001 - the dead local port refuses the connection
            return {"err": type(exc).__name__}
        return {"err": ""}

    g = StateGraph(_S)
    g.add_node("llm_node", node)
    g.add_edge(START, "llm_node")
    g.add_edge("llm_node", END)
    return g.compile()


@pytest.fixture
def dead_groq(monkeypatch):
    """ChatGroq pointed at a closed local port: the request starts, nothing leaves the host."""
    monkeypatch.setenv("GROQ_API_BASE", "http://127.0.0.1:9")


def test_groq_model_call_inside_a_node_is_nested_under_that_node(dead_groq):
    rec = Recorder()
    model = GroqChatModel("llama-test", "gsk_fake_key_for_test")
    graph = _groq_node_graph(model, rec)
    out = graph.invoke({}, config={"callbacks": [rec]})
    assert out["err"]  # the request really failed (connection refused)
    node_run = next(rid for n, rid, _ in rec.chains if n == "llm_node")
    assert [parent for _, parent in rec.models] == [node_run]


def test_groq_call_outside_a_graph_reports_under_the_trace_root(keyed, memory, dead_groq):
    model = GroqChatModel("llama-test", "gsk_fake_key_for_test")
    with trace_run(keyed, session_id="s", system="single_shot", input_text="t"), \
            pytest.raises(Exception):  # noqa: B017 - connection refused
        model.invoke("sys", "hello")
    from coding_agent.tracing import flush
    flush()
    spans = memory.get_finished_spans()
    root = next(s for s in spans if s.parent is None)
    gens = [s for s in spans if s.attributes.get("langfuse.observation.type") == "generation"]
    assert len(gens) == 1 and gens[0].parent.span_id == root.context.span_id
    assert gens[0].attributes.get("langfuse.observation.model.name") == "llama-test"


def test_real_graph_run_makes_one_trace_with_node_spans_and_a_summary(keyed, memory, settings):
    with trace_run(keyed, session_id="sess", system="graph", input_text="Print ok",
                   task_id="t1") as run:
        report = run_task(_graph(settings), "Print ok", config=run.config)
        run.set_report(report)
    from coding_agent.tracing import flush
    flush()
    spans = memory.get_finished_spans()
    assert len({s.context.trace_id for s in spans}) == 1
    names = {s.name for s in spans}
    assert set(NODES) <= names
    root = next(s for s in spans if s.parent is None)
    assert root.name == "coding-agent/graph"
    assert len(spans) < 30  # no duplicate callback registration blow-up
