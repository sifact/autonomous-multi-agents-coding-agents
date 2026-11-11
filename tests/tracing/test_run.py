"""A traced run, exported into memory: names, hierarchy, session, tags, masking, scores."""
import json
from types import SimpleNamespace

import pytest

from coding_agent.tracing import REDACTED, flush, trace_run

from .conftest import SECRET


def spans(exporter):
    flush()
    return exporter.get_finished_spans()


def attr(span, key):
    return span.attributes.get(key)


def test_disabled_run_is_a_noop(unkeyed):
    with trace_run(unkeyed, session_id="s", system="graph", task_id="t", input_text="x") as run:
        assert run.callbacks == [] and run.trace_id is None
        assert run.config == {}
        run.set_output({"success": True})
        run.score("final_pass", True)


def test_enabled_run_records_a_named_session_tagged_root(keyed, memory):
    with trace_run(keyed, session_id="sess-1", system="graph", task_id="fix_mean",
                   input_text="write a mean function", tags=["bug_fix"]) as run:
        assert len(run.callbacks) == 1 and run.trace_id
        assert run.config["metadata"]["langfuse_session_id"] == "sess-1"
        run.set_output({"success": True, "repairs": 1})
    root = next(s for s in spans(memory) if s.parent is None)
    assert root.name == "coding-agent/graph"
    assert attr(root, "langfuse.observation.type") == "agent"
    assert attr(root, "session.id") == "sess-1"
    assert set(attr(root, "langfuse.trace.tags")) == {"graph", "fix_mean", "bug_fix"}
    assert "write a mean function" in attr(root, "langfuse.observation.input")
    assert json.loads(attr(root, "langfuse.observation.output")) == {
        "success": True, "repairs": 1}


def test_secrets_in_input_and_output_are_masked(keyed, memory):
    with trace_run(keyed, session_id="s", system="graph", input_text=f"use {SECRET}") as run:
        run.set_output({"explanation": f"leaked {SECRET}"})
    root = next(s for s in spans(memory) if s.parent is None)
    blob = " ".join(str(v) for v in root.attributes.values())
    assert SECRET not in blob and REDACTED in blob


def test_error_inside_the_run_is_recorded_and_reraised(keyed, memory):
    with pytest.raises(ValueError, match="boom"), \
            trace_run(keyed, session_id="s", system="graph", input_text="x"):
        raise ValueError("boom")
    root = next(s for s in spans(memory) if s.parent is None)
    assert attr(root, "langfuse.observation.level") == "ERROR"
    assert "boom" in attr(root, "langfuse.observation.status_message")


def test_set_output_from_final_report_is_small_and_meaningful(keyed, memory):
    report = SimpleNamespace(
        success=True, files={"main.py": "x" * 5000}, explanation="done", repairs=2,
        usage=SimpleNamespace(tokens_in=10, tokens_out=5))
    with trace_run(keyed, session_id="s", system="graph", input_text="t") as run:
        run.set_report(report)
    root = next(s for s in spans(memory) if s.parent is None)
    out = json.loads(attr(root, "langfuse.observation.output"))
    assert out["success"] is True and out["repairs"] == 2 and out["explanation"] == "done"
    assert out["files"] == ["main.py"] and "x" * 100 not in json.dumps(out)


def test_score_is_sent_as_a_langfuse_score(keyed, memory, monkeypatch):
    sent = []
    with trace_run(keyed, session_id="s", system="graph", input_text="t") as run:
        client = run._client
        monkeypatch.setattr(client, "create_score", lambda **kw: sent.append(kw))
        run.score("final_pass", True)
        run.score("attempts", 3)
        trace_id = run.trace_id
    assert sent == [
        {"trace_id": trace_id, "name": "final_pass", "value": 1.0, "data_type": "BOOLEAN"},
        {"trace_id": trace_id, "name": "attempts", "value": 3.0, "data_type": "NUMERIC"},
    ]


def test_tracing_failures_never_break_the_run(keyed, monkeypatch, caplog):
    from coding_agent.tracing import langfuse_setup

    def boom(settings):
        raise RuntimeError("no network")
    monkeypatch.setattr(langfuse_setup, "_new_client", boom)
    langfuse_setup.reset()
    with trace_run(keyed, session_id="s", system="graph", input_text="x") as run:
        assert run.callbacks == []
        ran = True
    assert ran


def test_seeded_random_does_not_collide_trace_ids(keyed, memory):
    """The benchmark reseeds ``random`` before every task; trace ids must not follow it."""
    import random

    ids = []
    for _ in range(2):
        random.seed(0)
        with trace_run(keyed, session_id="s", system="graph", input_text="x") as run:
            ids.append(run.trace_id)
    assert ids[0] != ids[1]
