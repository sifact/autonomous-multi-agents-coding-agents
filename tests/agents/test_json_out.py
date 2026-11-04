import pytest
from pydantic import BaseModel

from coding_agent.agents import ParseError, invoke_json, parse_json
from coding_agent.graph import Verdict
from coding_agent.llm import FakeLLM


class Thing(BaseModel):
    name: str
    n: int


def test_plain_json():
    assert parse_json('{"name": "a", "n": 1}', Thing) == Thing(name="a", n=1)


def test_fenced_json_with_prose():
    text = 'Sure! Here it is:\n```json\n{"name": "a", "n": 2}\n```\nHope that helps {not json}'
    assert parse_json(text, Thing) == Thing(name="a", n=2)


def test_prose_around_bare_object_with_nested_braces():
    text = 'Answer: {"name": "x}y", "n": 3} trailing {"name": "z", "n": 9}'
    assert parse_json(text, Thing) == Thing(name="x}y", n=3)


def test_skips_invalid_candidate_and_finds_valid_one():
    text = 'thinking {not: json} then {"name": "b", "n": 4}'
    assert parse_json(text, Thing) == Thing(name="b", n=4)


def test_verdict_normalised():
    assert parse_json('{"action": " FIX "}', Verdict).action == "fix"


@pytest.mark.parametrize("text", ["", "no json here", '{"name": "a"}', '{"action": "maybe"}', "[1, 2]"])
def test_raises_parse_error(text):
    with pytest.raises(ParseError):
        parse_json(text, Thing)


def test_invoke_json_retries_once_then_gives_up():
    llm = FakeLLM(["garbage", "still garbage"])
    obj, usage, err = invoke_json(llm, "sys", "user", Thing)
    assert obj is None and "Thing" in err
    assert len(llm.calls) == 2
    assert "JSON" in llm.calls[1][1]  # the retry carries a reminder
    assert usage.total > 0


def test_invoke_json_success_first_try_makes_one_call():
    llm = FakeLLM(['{"name": "a", "n": 1}'])
    obj, _usage, err = invoke_json(llm, "sys", "user", Thing)
    assert obj == Thing(name="a", n=1) and err == "" and len(llm.calls) == 1


def test_invoke_json_recovers_on_retry():
    llm = FakeLLM(["oops", '{"name": "a", "n": 1}'])
    obj, _, _ = invoke_json(llm, "sys", "user", Thing)
    assert obj == Thing(name="a", n=1) and len(llm.calls) == 2


def test_prefer_last_picks_last_valid_object():
    text = '{"name": "first", "n": 1} junk {"bad": 1} {"name": "last", "n": 2}'
    assert parse_json(text, Thing).name == "first"
    assert parse_json(text, Thing, prefer="last").name == "last"


def test_invoke_json_passes_prefer():
    llm = FakeLLM(['{"name": "a", "n": 1} {"name": "b", "n": 2}'])
    obj, _, _ = invoke_json(llm, "s", "u", Thing, prefer="last")
    assert obj.name == "b"
