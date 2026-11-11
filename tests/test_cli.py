"""CLI tests: CliRunner, scripted models, injected factories. No network, no API key."""
import json

import pytest
from typer.testing import CliRunner

from coding_agent.cli import app
from coding_agent.cli_support import deps
from coding_agent.config import Settings
from coding_agent.evaluation.systems import SystemOutput
from coding_agent.llm import Usage
from tests.evaluation.helpers import TASKS
from tests.graph.fakes import code, layout, plan, scripted_router, verdict

runner = CliRunner()
IMAGE = "coding-agent-sandbox:latest"
SENTINEL = "gsk_SENTINEL_do_not_print_9f3a"


@pytest.fixture
def settings():
    return Settings(groq_api_key="test-key", sandbox_image=IMAGE, _env_file=None)


@pytest.fixture
def boom(monkeypatch):
    """Fail the test if anything builds a router or a sandbox."""
    def fail(*a, **k):
        raise AssertionError("router/sandbox must not be built for bad input")
    monkeypatch.setattr(deps, "make_router", fail)
    monkeypatch.setattr(deps, "make_sandbox", fail)


def _inject(monkeypatch, settings, **scripts):
    monkeypatch.setattr(deps, "load_settings", lambda: settings)
    monkeypatch.setattr(
        deps, "make_router",
        lambda s, tracker, all_strong=False: scripted_router(s, tracker, **scripts)[0],
    )


def test_help_lists_the_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("run", "eval", "safety", "report"):
        assert cmd in result.output


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0 and "coding-agent" in result.output


def test_report_is_a_registered_stub():
    result = runner.invoke(app, ["report"])
    assert result.exit_code == 0
    assert "Not implemented yet: see the README roadmap." in result.output


@pytest.mark.parametrize("task", ["", "   \n ", "x" * 4001])
def test_bad_task_exits_2_and_builds_nothing(boom, task):
    result = runner.invoke(app, ["run", task])
    assert result.exit_code == 2
    assert "task" in result.output.lower()


def test_task_of_exactly_4000_chars_is_accepted(monkeypatch, settings):
    monkeypatch.setattr(deps, "load_settings", lambda: settings)
    seen = []

    def stop(*a, **k):
        seen.append(1)
        raise deps.SetupError("stop here")

    monkeypatch.setattr(deps, "make_router", stop)
    result = runner.invoke(app, ["run", "x" * 4000])
    assert seen and result.exit_code == 3


def test_missing_key_exits_3_with_message(monkeypatch):
    monkeypatch.setattr(
        deps, "load_settings", lambda: Settings(groq_api_key=None, _env_file=None)
    )
    monkeypatch.setattr(deps, "make_sandbox", lambda s: pytest.fail("sandbox built"))
    result = runner.invoke(app, ["run", "print hi"])
    assert result.exit_code == 3
    assert "GROQ_API_KEY is not set. Copy .env.example to .env and add your key" in result.output


def test_docker_down_exits_3_with_hint(monkeypatch, settings):
    monkeypatch.setattr(deps, "load_settings", lambda: settings)
    monkeypatch.setattr(deps, "_docker", lambda *args: (1, "Cannot connect"))
    result = runner.invoke(app, ["safety"])
    assert result.exit_code == 3
    assert "colima start" in result.output


def test_missing_image_exits_3_with_build_command(monkeypatch, settings):
    monkeypatch.setattr(deps, "load_settings", lambda: settings)
    monkeypatch.setattr(
        deps, "_docker", lambda *args: (0, "") if args[0] == "info" else (1, "no such image")
    )
    result = runner.invoke(app, ["safety"])
    assert result.exit_code == 3
    assert "docker build -t coding-agent-sandbox:latest -f docker/sandbox.Dockerfile ." in (
        result.output
    )


@pytest.mark.docker
def test_run_success_prints_steps_and_writes_files(monkeypatch, settings, tmp_path):
    _inject(
        monkeypatch, settings, planner=[plan()], architect=[layout()],
        coder=[code("print('ok')")], reviewer=[verdict("pass", "prints ok")],
    )
    out = tmp_path / "out"
    result = runner.invoke(app, ["run", "Print ok", "--out", str(out)])
    assert result.exit_code == 0, result.output
    text = result.output
    assert "plan a" in text and "prints ok" in text  # plan + criteria
    assert "main.py" in text  # layout and code version
    assert "exit code 0" in text
    assert "pass" in text.lower()
    assert "SUCCESS" in text
    assert "n/a" in text and "$0" not in text  # fake model has no known price
    assert (out / "main.py").read_text().strip() == "print('ok')"
    assert str(out) in text


@pytest.mark.docker
def test_run_failure_exits_1_and_explains(monkeypatch, settings, tmp_path):
    _inject(
        monkeypatch, settings, planner=[plan()], architect=[layout()],
        coder=[code("raise SystemExit(3)")], reviewer=[verdict("stop", "cannot be fixed")],
    )
    result = runner.invoke(app, ["run", "Print ok", "--out", str(tmp_path / "o")])
    assert result.exit_code == 1
    assert "FAILED" in result.output
    assert "Reviewer stopped the run: cannot be fixed" in result.output


@pytest.mark.docker
def test_quiet_prints_only_the_summary(monkeypatch, settings, tmp_path):
    _inject(
        monkeypatch, settings, planner=[plan()], architect=[layout()],
        coder=[code("print('ok')")], reviewer=[verdict("pass")],
    )
    result = runner.invoke(app, ["run", "Print ok", "--quiet", "--out", str(tmp_path / "o")])
    assert result.exit_code == 0
    assert "SUCCESS" in result.output and "plan a" not in result.output


@pytest.mark.docker
def test_run_never_prints_the_api_key(monkeypatch, tmp_path):
    monkeypatch.setenv("GROQ_API_KEY", SENTINEL)
    settings = Settings(sandbox_image=IMAGE, _env_file=None)
    assert settings.groq_api_key.get_secret_value() == SENTINEL
    _inject(
        monkeypatch, settings, planner=[plan()], architect=[layout()],
        coder=[code("print('ok')")], reviewer=[verdict("pass")],
    )
    result = runner.invoke(app, ["run", "Print ok", "--out", str(tmp_path / "o")])
    assert result.exit_code == 0
    assert SENTINEL not in result.output


class ScriptedSystem:
    name = "graph"

    def solve(self, task):
        files = dict(task.reference)
        return SystemOutput(
            files=files, attempts=2, first_try_pass=False, had_runtime_error=True, fixed=True,
            usage=Usage(100, 50), cost_usd=None, wall_s=1.5,
        )

    def describe(self):
        return {"models": {"m": "fake"}, "settings": {}}


@pytest.mark.docker
def test_eval_writes_results_and_prints_summary(monkeypatch, settings, tmp_path):
    monkeypatch.setattr(deps, "load_settings", lambda: settings)
    monkeypatch.setattr(deps, "tasks_dir", lambda: TASKS)
    monkeypatch.setattr(
        deps, "make_router", lambda s, tracker, all_strong=False: scripted_router(s, tracker)[0]
    )
    monkeypatch.setattr(deps, "build_system", lambda *a, **k: ScriptedSystem())
    result = runner.invoke(
        app, ["eval", "--system", "graph", "--subset", "full", "--out-dir", str(tmp_path)]
    )
    assert result.exit_code == 0, result.output
    assert "fix_mean" in result.output and "sum_csv" in result.output
    assert "PASS" in result.output
    assert "pass@1" in result.output and "n/a" in result.output and "$0" not in result.output
    files = list(tmp_path.glob("graph-*.json"))
    assert len(files) == 1 and str(files[0]) in result.output
    assert len(json.loads(files[0].read_text())["records"]) == 2


def test_eval_rejects_unknown_system():
    result = runner.invoke(app, ["eval", "--system", "nope", "--subset", "fast"])
    assert result.exit_code == 2


@pytest.mark.docker
def test_safety_runs_for_real_and_exits_0(monkeypatch, settings):
    monkeypatch.setattr(deps, "load_settings", lambda: settings)
    result = runner.invoke(app, ["safety"])
    assert result.exit_code == 0, result.output
    assert "disk_fill" in result.output and "PASS" in result.output
    assert "7/7" in result.output


def test_safety_exits_1_when_a_case_fails(monkeypatch, settings):
    from coding_agent.evaluation import CaseResult, SafetyReport
    monkeypatch.setattr(deps, "load_settings", lambda: settings)
    monkeypatch.setattr(deps, "make_sandbox", lambda s: object())
    monkeypatch.setattr(
        deps, "run_safety_suite",
        lambda sb: SafetyReport([CaseResult("a", True), CaseResult("b", False, "leaked")]),
    )
    result = runner.invoke(app, ["safety"])
    assert result.exit_code == 1
    assert "FAIL" in result.output and "1/2" in result.output


# ---- fix round 1 -------------------------------------------------------------------------

ESCAPES = "\x1b]0;title\x07 \x1b[2J \x07 \x9b31m \x85"
BAD_BYTES = ("\x1b", "\x07", "\x9b", "\x85", "\x9d")


def _fake_stream(monkeypatch, settings, updates, files=None, success=True):
    """Bypass the graph: ``updates`` is a list of (node, update) or an exception to raise."""
    from coding_agent.graph.state import FinalReport

    monkeypatch.setattr(deps, "load_settings", lambda: settings)
    monkeypatch.setattr(deps, "make_router", lambda s, t, all_strong=False: object())
    monkeypatch.setattr(deps, "make_sandbox", lambda s: object())
    monkeypatch.setattr("coding_agent.cli.build_graph", lambda *a, **k: None)

    def stream(graph, task, fixtures=None, config=None):
        for u in updates:
            if isinstance(u, BaseException):
                raise u
            yield u
        yield "finalize", {"final": FinalReport(
            success=success, files=files or {}, explanation="done", repairs=0, usage=Usage(1, 1),
        )}

    monkeypatch.setattr("coding_agent.cli.stream_task", stream)


@pytest.mark.docker
def test_model_path_escape_is_repaired_not_a_crash(monkeypatch, settings, tmp_path):
    _inject(
        monkeypatch, settings, planner=[plan()], architect=[layout()],
        coder=["### FILE: ../evil.py\n```python\nprint(1)\n```\n"],
        debugger=[code("print('ok')")],
        reviewer=[verdict("fix", "no files"), verdict("pass")],
    )
    out = tmp_path / "out"
    result = runner.invoke(app, ["run", "Print ok", "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert "SUCCESS" in result.output and "TypeError" not in result.output
    assert "../evil.py" in result.output  # reported as dropped
    assert "not run" in result.output
    assert not (tmp_path / "evil.py").exists()
    assert (out / "main.py").exists()


def test_final_files_with_escaping_path_are_refused_and_reported(monkeypatch, settings, tmp_path):
    _fake_stream(monkeypatch, settings, [], files={"../x.py": "print(1)"})
    result = runner.invoke(app, ["run", "t", "--out", str(tmp_path / "out")])
    assert result.exit_code == 3
    assert "Files NOT written" in result.output
    assert not (tmp_path / "x.py").exists()
    assert "print(1)" in result.output  # code is shown so nothing is lost
    assert "SUCCESS" in result.output  # full summary still printed


def test_out_pointing_at_a_file_is_clean(monkeypatch, settings, tmp_path):
    _fake_stream(monkeypatch, settings, [], files={"main.py": "print(7)"})
    target = tmp_path / "afile"
    target.write_text("x")
    result = runner.invoke(app, ["run", "t", "--out", str(target)])
    assert result.exit_code == 3
    assert "Files NOT written" in result.output and "print(7)" in result.output
    assert "Traceback" not in result.output


def test_unwritable_out_dir_is_clean(monkeypatch, settings, tmp_path):
    import os
    ro = tmp_path / "ro"
    ro.mkdir()
    ro.chmod(0o500)
    try:
        if os.access(ro, os.W_OK):
            pytest.skip("running as a user that can write to read-only dirs")
        _fake_stream(monkeypatch, settings, [], files={"main.py": "print(7)"})
        result = runner.invoke(app, ["run", "t", "--out", str(ro / "sub")])
    finally:
        ro.chmod(0o700)
    assert result.exit_code == 3 and "Files NOT written" in result.output
    assert "Traceback" not in result.output


def test_summary_shows_attempts(monkeypatch, settings, tmp_path):
    _fake_stream(monkeypatch, settings, [], files={"main.py": "1"})
    result = runner.invoke(app, ["run", "t", "--out", str(tmp_path / "o")])
    assert "attempts:" in result.output


def test_keyboard_interrupt_exits_130(monkeypatch, settings, tmp_path):
    _fake_stream(monkeypatch, settings, [KeyboardInterrupt()])
    result = runner.invoke(app, ["run", "t", "--out", str(tmp_path / "o")])
    assert result.exit_code == 130
    assert "Interrupted" in result.output and "Traceback" not in result.output


def test_wrong_key_exits_3_without_echoing_key(monkeypatch, settings):
    import groq

    class Auth(groq.AuthenticationError):
        def __init__(self):
            Exception.__init__(self, f"401 bad key {settings.groq_api_key.get_secret_value()}")

    _fake_stream(monkeypatch, settings, [Auth()])
    result = runner.invoke(app, ["run", "t"])
    assert result.exit_code == 3
    assert "Groq rejected GROQ_API_KEY (401). Check the key in .env." in result.output
    assert "test-key" not in result.output


def test_other_api_error_is_exit_1_and_clean(monkeypatch, settings):
    _fake_stream(monkeypatch, settings, [RuntimeError("boom")])
    result = runner.invoke(app, ["run", "t"])
    assert result.exit_code == 1 and "boom" in result.output
    assert "Traceback" not in result.output


def test_all_strong_reaches_the_router(monkeypatch, settings, tmp_path):
    seen = []
    _fake_stream(monkeypatch, settings, [], files={"main.py": "1"})
    monkeypatch.setattr(
        deps, "make_router", lambda s, t, all_strong=False: seen.append(all_strong) or object()
    )
    runner.invoke(app, ["run", "t", "--all-strong", "--out", str(tmp_path / "o")])
    assert seen == [True]


def test_escape_sequences_in_model_text_never_reach_output(monkeypatch, settings, tmp_path):
    from coding_agent.graph.state import Step, Verdict
    from coding_agent.sandbox import ExecResult

    res = ExecResult(1, f"out {ESCAPES}", f"err {ESCAPES}", False, False, 0.1)
    _fake_stream(
        monkeypatch, settings,
        [
            ("planner", {"plan": [Step(id=1, description=f"d{ESCAPES}", acceptance="a")],
                         "criteria": [f"c{ESCAPES}"]}),
            ("executor", {"code_versions": [{
                "version": 1, "command": ["python", f"m{ESCAPES}.py"], "summary": "s",
                "flags": []}], "last_exec": res}),
            ("reviewer", {"verdict": Verdict(action="fix", reason=f"r{ESCAPES}")}),
        ],
        files={f"f{ESCAPES}.py": "1"},
    )
    result = runner.invoke(app, ["run", "t", "--out", str(tmp_path / "o")])
    for bad in BAD_BYTES:
        assert bad not in result.output
    assert "[2J" not in result.output and "title" not in result.output
    assert "31m" not in result.output


@pytest.mark.docker
def test_program_output_escapes_stripped_end_to_end(monkeypatch, settings, tmp_path):
    body = "import sys\nprint('\\x1b]0;pwn\\x07\\x1b[2J\\x9b31m hi')\nsys.exit(1)"
    _inject(
        monkeypatch, settings, planner=[plan()], architect=[layout()], coder=[code(body)],
        reviewer=[verdict("stop", "bad\x1b[2J")],
    )
    result = runner.invoke(app, ["run", "t", "--out", str(tmp_path / "o")])
    assert result.exit_code == 1
    for bad in BAD_BYTES:
        assert bad not in result.output
    assert "]0;" not in result.output and "[2J" not in result.output
    assert "31m" not in result.output


# ---- eval ---------------------------------------------------------------------------------


def test_eval_missing_key_exits_3_before_docker_or_tasks(monkeypatch):
    monkeypatch.setattr(
        deps, "load_settings", lambda: Settings(groq_api_key=None, _env_file=None)
    )
    monkeypatch.setattr(deps, "make_sandbox", lambda s: pytest.fail("sandbox built"))
    monkeypatch.setattr(deps, "tasks_dir", lambda: pytest.fail("tasks loaded"))
    result = runner.invoke(app, ["eval", "--system", "graph", "--subset", "fast"])
    assert result.exit_code == 3
    assert "GROQ_API_KEY is not set. Copy .env.example to .env and add your key" in result.output


def _eval_env(monkeypatch, settings, solved):
    class Sys(ScriptedSystem):
        def solve(self, task):
            solved.append(task.id)
            return super().solve(task)

    monkeypatch.setattr(deps, "load_settings", lambda: settings)
    monkeypatch.setattr(deps, "make_router", lambda s, t, all_strong=False: object())
    monkeypatch.setattr(deps, "make_sandbox", lambda s: GoodSandbox())
    monkeypatch.setattr(deps, "build_system", lambda *a, **k: Sys())


class GoodSandbox:
    def run(self, workspace, command, limits=None):
        from coding_agent.sandbox import ExecResult
        return ExecResult(0, "1 passed", "", False, False, 0.1)


def test_fast_subset_selects_exactly_the_listed_ids(monkeypatch, settings, tmp_path):
    from coding_agent.evaluation.runner import REPO_ROOT
    solved: list[str] = []
    _eval_env(monkeypatch, settings, solved)
    result = runner.invoke(
        app, ["eval", "--system", "graph", "--subset", "fast", "--out-dir", str(tmp_path)]
    )
    ids = [
        ln.strip() for ln in (REPO_ROOT / "benchmarks" / "fast_subset.txt").read_text().splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    assert result.exit_code == 0, result.output
    assert solved == ids and len(ids) == 10


def test_eval_on_saved_path_is_printed_even_on_failure(monkeypatch, settings, tmp_path):
    class Crash(ScriptedSystem):
        def solve(self, task):
            raise RuntimeError("down")

    _eval_env(monkeypatch, settings, [])
    monkeypatch.setattr(deps, "build_system", lambda *a, **k: Crash())
    monkeypatch.setattr(deps, "tasks_dir", lambda: TASKS)
    result = runner.invoke(
        app, ["eval", "--system", "graph", "--subset", "full", "--out-dir", str(tmp_path)]
    )
    # two tasks only: fewer than 3 consecutive crashes, so the run completes with n_errors=2
    assert result.exit_code == 0 and "n_errors" in result.output
    assert "Results written to" in result.output


def test_eval_states_all_strong_is_a_noop_for_baselines(monkeypatch, settings, tmp_path):
    _eval_env(monkeypatch, settings, [])
    monkeypatch.setattr(deps, "tasks_dir", lambda: TASKS)
    result = runner.invoke(app, [
        "eval", "--system", "single_shot", "--subset", "full", "--all-strong",
        "--out-dir", str(tmp_path),
    ])
    assert "--all-strong has no effect" in result.output


@pytest.mark.docker
def test_key_never_printed_on_failure_or_eval(monkeypatch, tmp_path):
    monkeypatch.setenv("GROQ_API_KEY", SENTINEL)
    settings = Settings(sandbox_image=IMAGE, _env_file=None)
    _inject(
        monkeypatch, settings, planner=[plan()], architect=[layout()],
        coder=[code("raise SystemExit(2)")], reviewer=[verdict("stop", "nope")],
    )
    r1 = runner.invoke(app, ["run", "t", "--out", str(tmp_path / "o")])
    assert r1.exit_code == 1 and SENTINEL not in r1.output
    monkeypatch.setattr(deps, "tasks_dir", lambda: TASKS)
    monkeypatch.setattr(deps, "build_system", lambda *a, **k: ScriptedSystem())
    r2 = runner.invoke(
        app, ["eval", "--system", "graph", "--subset", "full", "--out-dir", str(tmp_path)]
    )
    assert r2.exit_code == 0 and SENTINEL not in r2.output
    saved = "".join(p.read_text() for p in tmp_path.glob("*.json"))
    assert SENTINEL not in saved
