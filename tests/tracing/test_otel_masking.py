"""Everything that leaves the process is scrubbed: attributes, status, events, names."""
import json

import pytest
from langchain_core.callbacks import BaseCallbackHandler  # noqa: F401

from coding_agent.tracing import REDACTED, flush, trace_run

from .conftest import SECRET

GROQ = "gsk_" + "SENTINEL123456789"
OPENAI = "sk-proj-" + "SENTINELabcdef123456789"
SENTINELS = (GROQ, OPENAI, SECRET, "SENTINEL123")


def everything(span) -> str:
    """Every string a span would carry out of the process."""
    parts = [span.name, span.status.description or "", json.dumps(dict(span.attributes),
                                                                   default=str)]
    for ev in span.events:
        parts += [ev.name, json.dumps(dict(ev.attributes or {}), default=str)]
    return "\n".join(parts)


def assert_clean(memory):
    flush()
    spans = memory.get_finished_spans()
    assert spans
    blob = "\n".join(everything(s) for s in spans)
    for s in SENTINELS:
        assert s not in blob, s
    return blob


def test_exception_message_and_stack_trace_inside_trace_run_are_scrubbed(keyed, memory):
    with pytest.raises(RuntimeError), trace_run(keyed, session_id="s", system="graph",
                                                input_text="x"):
        raise RuntimeError(f"401 Incorrect API key provided: {GROQ}")
    blob = assert_clean(memory)
    assert REDACTED in blob and "Incorrect API key" in blob


def test_status_message_and_span_name_are_scrubbed(keyed, memory):
    with trace_run(keyed, session_id="s", system="graph", input_text="x") as run:
        run._root.update(level="ERROR", status_message=f"bad {OPENAI}")
        run._client.start_observation(name=f"tool {GROQ}", as_type="span").end()
    assert_clean(memory)


def test_otel_status_description_and_event_attributes_are_scrubbed(keyed, memory):
    from opentelemetry.trace import Status, StatusCode

    with trace_run(keyed, session_id="s", system="graph", input_text="x") as run:
        otel = run._root._otel_span
        otel.set_status(Status(StatusCode.ERROR, f"boom {GROQ}"))
        otel.add_event(f"evt {OPENAI}", {"detail": f"token {GROQ}", "n": 3})
        otel.record_exception(ValueError(f"leak {SECRET}"))
    blob = assert_clean(memory)
    assert REDACTED in blob


def test_handler_error_text_is_scrubbed(keyed, memory):
    handler = trace_run_handler = None
    from uuid import uuid4

    with trace_run(keyed, session_id="s", system="graph", input_text="x") as run:
        handler = run.callbacks[0]
        rid = uuid4()
        handler.on_chain_start({"name": "n"}, {"a": 1}, run_id=rid, name="node")
        handler.on_chain_error(RuntimeError(f"401 {GROQ}"), run_id=rid)
    assert trace_run_handler is None
    assert_clean(memory)


def test_a_failing_scrubber_fails_closed(keyed, memory, monkeypatch):
    from coding_agent.tracing import scrub_spans

    def explode(scrub, text):
        raise RuntimeError("scrubber bug")

    monkeypatch.setattr(scrub_spans, "_scrub_once", explode)
    with trace_run(keyed, session_id="s", system="graph", input_text=f"x {GROQ}") as run:
        run._root.update(level="ERROR", status_message=f"bad {GROQ}")
    flush()
    blob = "\n".join(everything(s) for s in memory.get_finished_spans())
    assert GROQ not in blob


def test_record_error_scrubs_its_message(keyed, memory):
    with trace_run(keyed, session_id="s", system="graph", input_text="x") as run:
        run.record_error(RuntimeError(f"fail {GROQ}"))
    assert_clean(memory)
