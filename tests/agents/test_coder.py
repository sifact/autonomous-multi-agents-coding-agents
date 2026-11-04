from coding_agent.agents import make_coder, parse_files
from coding_agent.llm import FakeLLM

TWO_FILES = """Here you go.
### FILE: main.py
```python
from util import f
print(f())
```

### FILE: pkg/util.py
```
def f():
    return "```not a fence end```"
```
"""


def test_parse_files_delimiter_format():
    files = parse_files(TWO_FILES)
    assert set(files) == {"main.py", "pkg/util.py"}
    assert files["main.py"] == "from util import f\nprint(f())\n"
    assert 'return "```not a fence end```"' in files["pkg/util.py"]


def test_parse_files_json_fallback():
    assert parse_files('```json\n{"files": {"main.py": "print(1)\\n"}}\n```') == {"main.py": "print(1)\n"}


def test_parse_files_nothing():
    assert parse_files("I cannot do that.") == {}


def test_first_write_uses_coder_model(state):
    coder = FakeLLM(["### FILE: main.py\n```python\nprint('ok')\n```"])
    debugger = FakeLLM([])
    update = make_coder(coder, debugger)(state)
    assert update["files"] == {"main.py": "print('ok')\n"}
    assert len(coder.calls) == 1 and debugger.calls == []
    assert update["visits"] == state["visits"] + 1
    assert "repairs" not in update
    assert update["events"][0]["node"] == "coder" and update["events"][0]["role"] == "coder"
    assert "main.py: entry point" in coder.calls[0][1]


def test_fix_verdict_uses_debugger_and_counts_repair(reviewed_state):
    coder = FakeLLM([])
    debugger = FakeLLM(["### FILE: main.py\n```python\nprint('ok')\n```"])
    update = make_coder(coder, debugger)(reviewed_state)
    assert coder.calls == [] and len(debugger.calls) == 1
    assert (update["repairs"], update["verdict"]) == (1, None)
    prompt = debugger.calls[0][1]
    assert "ZeroDivisionError" in prompt and "divide by zero on line 1" in prompt and "print(1/0)" in prompt
    assert update["events"][0]["role"] == "debugger"


def test_single_model_serves_both_roles(reviewed_state):
    llm = FakeLLM(["### FILE: main.py\n```python\nprint('ok')\n```"])
    assert make_coder(llm)(reviewed_state)["repairs"] == 1
