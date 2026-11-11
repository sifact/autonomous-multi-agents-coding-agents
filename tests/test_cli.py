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
    assert settings.groq_api_key == SENTINEL
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
