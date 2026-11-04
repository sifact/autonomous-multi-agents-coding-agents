"""Fixtures must be both TOLD to the model and PRESENT in the run workspace."""
import pytest

from coding_agent.agents import execute_files, make_executor
from coding_agent.agents.prompts import FIXTURE_PREVIEW_CHARS, FIXTURE_PREVIEW_LINES
from coding_agent.config import Settings
from coding_agent.evaluation import (
    GraphSystem,
    SingleAgentLoop,
    SingleShot,
    grade,
    load_tasks,
)
from coding_agent.graph import initial_state
from coding_agent.llm import FakeLLM
from coding_agent.sandbox import DockerSandbox, ExecResult
from tests.graph.fakes import layout, plan, scripted_router, verdict

from .helpers import TASKS

SUM_CSV = {t.id: t for t in load_tasks(TASKS)}["sum_csv"]
IMAGE = "coding-agent-sandbox:latest"
READER = (
    "import csv\n"
    "rows = list(csv.DictReader(open('data.csv', newline='')))\n"
    "print(sum(float(r['amount']) for r in rows))\n"
)


class SeeingSandbox:
    def __init__(self):
        self.seen = {}

    def run(self, workspace, command, limits=None):
        self.seen = {p.relative_to(workspace).as_posix(): p.read_text()
                     for p in workspace.rglob("*") if p.is_file()}
        return ExecResult(0, "", "", False, False, 0.0)


def test_fixture_overrides_agent_file_of_same_name():
    sb = SeeingSandbox()
    execute_files({"main.py": "x=1", "data.csv": "EVIL"}, sb, Settings(),
                  fixtures={"data.csv": "real"})
    assert sb.seen["data.csv"] == "real" and "main.py" in sb.seen


def test_initial_state_fixtures_default_and_set():
    assert initial_state("t")["fixtures"] == {}
    assert initial_state("t", {"a": "b"})["fixtures"] == {"a": "b"}


def test_executor_node_writes_state_fixtures():
    sb = SeeingSandbox()
    s = initial_state("t", {"data.csv": "a,b\n"})
    s["files"] = {"main.py": "print(1)"}
    make_executor(sb, Settings())(s)
    assert sb.seen["data.csv"] == "a,b\n"


def _assert_told(prompt: str):
    assert "data.csv" in prompt and "rent,1200.50" in prompt
    assert "present in the working directory" in prompt


def test_single_shot_and_loop_prompts_contain_fixture_preview():
    llm = FakeLLM(["x"])
    SingleShot(llm, SeeingSandbox(), model_name="m").solve(SUM_CSV)
    _assert_told(llm.calls[0][1])
    llm = FakeLLM(["x"] * 4)
    SingleAgentLoop(llm, SeeingSandbox(), Settings(), model_name="m").solve(SUM_CSV)
    _assert_told(llm.calls[0][1])


def test_preview_is_capped():
    assert FIXTURE_PREVIEW_LINES == 20 and FIXTURE_PREVIEW_CHARS == 1500
    from dataclasses import replace
    big = replace(SUM_CSV, fixtures={"big.txt": "\n".join(f"line{i}" for i in range(500))})
    llm = FakeLLM(["x"])
    SingleShot(llm, SeeingSandbox(), model_name="m").solve(big)
    assert "line19" in llm.calls[0][1] and "line25" not in llm.calls[0][1]


def test_graph_nodes_all_see_fixtures():
    settings = Settings()
    router, llms = scripted_router(
        settings, planner=[plan()], architect=[layout()],
        coder=["### FILE: main.py\n```python\nprint(1)\n```\n"], reviewer=[verdict("pass")],
    )
    GraphSystem(lambda t: router, SeeingSandbox(), settings).solve(SUM_CSV)
    for role in ("planner", "architect", "coder", "reviewer"):
        _assert_told(llms[role].calls[0][1])


def test_debugger_sees_fixtures():
    settings = Settings()
    bad = "### FILE: main.py\n```python\nprint(1)\n```\n"

    class Fails(SeeingSandbox):
        n = 0

        def run(self, workspace, command, limits=None):
            self.n += 1
            return ExecResult(1 if self.n == 1 else 0, "", "boom", False, False, 0.0)

    router, llms = scripted_router(
        settings, planner=[plan()], architect=[layout()], coder=[bad], debugger=[bad],
        reviewer=[verdict("fix"), verdict("pass")],
    )
    GraphSystem(lambda t: router, Fails(), settings).solve(SUM_CSV)
    _assert_told(llms["debugger"].calls[0][1])


@pytest.mark.docker
def test_real_sandbox_program_reads_fixture():
    settings = Settings(sandbox_image=IMAGE)
    _, result = execute_files(
        {"main.py": READER}, DockerSandbox(IMAGE), settings, fixtures=SUM_CSV.fixtures
    )
    assert result.exit_code == 0 and result.stdout.strip() == "1600.0"


@pytest.mark.docker
def test_sum_csv_end_to_end_through_graph_system():
    settings = Settings(sandbox_image=IMAGE)
    ref = SUM_CSV.reference["solution.py"]
    coder = (f"### FILE: solution.py\n```python\n{ref}\n```\n"
             f"### FILE: main.py\n```python\n{READER}```\n")
    router, _ = scripted_router(
        settings, planner=[plan()], architect=[layout()], coder=[coder], reviewer=[verdict("pass")],
    )
    sandbox = DockerSandbox(IMAGE)
    out = GraphSystem(lambda t: router, sandbox, settings).solve(SUM_CSV)
    assert out.had_runtime_error is False and out.first_try_pass is True
    assert grade(SUM_CSV, out.files, sandbox).passed
