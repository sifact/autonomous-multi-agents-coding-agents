from coding_agent.agents import make_reviewer
from coding_agent.llm import FakeLLM
from coding_agent.sandbox import ExecResult

from .conftest import failed_exec, ok_exec


def _ready(state, exec_result, flags=()):
    state["files"] = {"main.py": "print('ok')"}
    state["last_exec"] = exec_result
    state["code_versions"] = [{"version": 1, "files": state["files"], "flags": list(flags)}]
    state["repairs"], state["replans"] = 2, 1
    return state


def test_pass_on_success_and_event_recorded(state):
    llm = FakeLLM(['```json\n{"action": "pass", "reason": "prints ok"}\n```'])
    update = make_reviewer(llm)(_ready(state, ok_exec()))
    assert update["verdict"].action == "pass"
    assert update["visits"] == state["visits"] + 1
    ev = update["events"][0]
    assert (ev["node"], ev["action"], ev["reason"]) == ("reviewer", "pass", "prints ok")
    assert not {"repairs", "replans"} & update.keys()  # the reviewer never bumps counters
    assert len(llm.calls) == 1


def test_prompt_shows_everything_the_reviewer_needs(state):
    flags = [{"path": "main.py", "rule": "shell_exec", "line": 3}]
    llm = FakeLLM(['{"action": "fix", "reason": "r"}'])
    make_reviewer(llm)(_ready(state, ExecResult(1, "partial out", "Boom: bad", True, True, 30.0), flags))
    prompt = llm.calls[0][1]
    for needle in ("Print ok", "prints ok", "print('ok')", "exit code 1", "partial out", "Boom: bad",
                   "timed out", "out of memory", "shell_exec", "Repairs so far: 2", "Replans so far: 1"):
        assert needle in prompt, needle


def test_pass_with_failed_run_is_downgraded_to_fix(state):
    llm = FakeLLM(['{"action": "pass", "reason": "looks fine"}'])
    update = make_reviewer(llm)(_ready(state, failed_exec()))
    v = update["verdict"]
    assert v.action == "fix" and "exit code 1" in v.reason
    assert update["events"][0]["action"] == "fix"


def test_pass_with_timeout_is_downgraded_to_fix(state):
    llm = FakeLLM(['{"action": "pass"}'])
    update = make_reviewer(llm)(_ready(state, ExecResult(0, "", "", True, False, 30.0)))
    assert update["verdict"].action == "fix" and "timed out" in update["verdict"].reason


def test_malformed_then_failed_retry_stops(state):
    llm = FakeLLM(["I think it is fine!", '{"action": "maybe"}'])
    update = make_reviewer(llm)(_ready(state, ok_exec()))
    v = update["verdict"]
    assert v.action == "stop" and "malformed" in v.reason.lower()
    assert len(llm.calls) == 2
    assert update["events"][0]["action"] == "stop"


def test_malformed_then_good_retry(state):
    llm = FakeLLM(["hmm", '{"action": "fix", "reason": "x"}'])
    assert make_reviewer(llm)(_ready(state, failed_exec()))["verdict"].action == "fix"
    assert len(llm.calls) == 2
