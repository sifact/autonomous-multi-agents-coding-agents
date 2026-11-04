import pytest

from coding_agent.llm import FakeLLM, LLMResponse, Usage
from coding_agent.llm.fake import ScriptExhaustedError


def test_returns_scripted_replies_in_order_and_records_calls():
    llm = FakeLLM(["a", "b"])
    r1 = llm.invoke("sys1", "user1")
    r2 = llm.invoke("sys2", "user2")
    assert isinstance(r1, LLMResponse)
    assert (r1.text, r2.text) == ("a", "b")
    assert llm.calls == [("sys1", "user1"), ("sys2", "user2")]


def test_usage_is_a_simple_token_estimate():
    r = FakeLLM(["x" * 40]).invoke("s" * 40, "u" * 40)
    assert r.usage == Usage(tokens_in=20, tokens_out=10)


def test_exhaustion_raises_clear_error():
    llm = FakeLLM(["only"])
    llm.invoke("s", "u")
    with pytest.raises(ScriptExhaustedError, match="1 scripted"):
        llm.invoke("s", "u")
