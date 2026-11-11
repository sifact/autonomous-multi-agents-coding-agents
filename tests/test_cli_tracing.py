"""CLI tracing: the status line, flushing on every exit path, and failure isolation."""
from contextlib import contextmanager

import pytest
from typer.testing import CliRunner

from coding_agent.cli import app
from coding_agent.cli_support import deps
from coding_agent.config import Settings
from coding_agent.tracing import TraceRun, langfuse_setup
from tests.evaluation.helpers import TASKS
from tests.test_cli import GoodSandbox, ScriptedSystem, _fake_stream

runner = CliRunner()
PUBLIC, SECRET = "pk-lf-CLIPUBLIC0000", "sk-lf-CLISECRET0000"
OFF = "Langfuse tracing: off (set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY to enable)"


@pytest.fixture
def plain():
    return Settings(groq_api_key="test-key", _env_file=None)


@pytest.fixture
def keyed():
    return Settings(groq_api_key="test-key", langfuse_public_key=PUBLIC,
                    langfuse_secret_key=SECRET, langfuse_host="http://127.0.0.1:9",
                    _env_file=None)


@pytest.fixture
def flushes(monkeypatch):
    calls = []
    monkeypatch.setattr(deps, "flush_traces", lambda *a: calls.append(1))
    return calls


def test_run_prints_off_line_without_keys(monkeypatch, plain, flushes, tmp_path):
    _fake_stream(monkeypatch, plain, [], files={"main.py": "1"})
    result = runner.invoke(app, ["run", "t", "--out", str(tmp_path / "o")])
    assert OFF in result.output and result.exit_code == 0


def test_run_prints_on_line_with_host_and_never_a_key(monkeypatch, keyed, flushes, tmp_path):
    _fake_stream(monkeypatch, keyed, [], files={"main.py": "1"})
    seen = {}

    @contextmanager
    def fake_trace(settings, **kw):
        seen.update(kw)
        yield TraceRun()

    monkeypatch.setattr(deps, "trace_run", fake_trace)
    result = runner.invoke(app, ["run", "t", "--out", str(tmp_path / "o")])
    assert "Langfuse tracing: on (http://127.0.0.1:9)" in result.output
    assert PUBLIC not in result.output and SECRET not in result.output
    assert seen["system"] == "graph" and seen["input_text"] == "t"


def test_flush_runs_on_success_failure_and_interrupt(monkeypatch, plain, flushes, tmp_path):
    out = str(tmp_path / "o")
    _fake_stream(monkeypatch, plain, [], files={"main.py": "1"})
    assert runner.invoke(app, ["run", "t", "--out", out]).exit_code == 0
    assert len(flushes) == 1
    _fake_stream(monkeypatch, plain, [RuntimeError("boom")])
    assert runner.invoke(app, ["run", "t"]).exit_code == 1
    assert len(flushes) == 2
    _fake_stream(monkeypatch, plain, [KeyboardInterrupt()])
    assert runner.invoke(app, ["run", "t"]).exit_code == 130
    assert len(flushes) == 3


def test_stream_receives_the_trace_config_and_report_is_recorded(
        monkeypatch, plain, flushes, tmp_path):
    received = {}
    reports = []

    class Spy(TraceRun):
        def __init__(self):
            super().__init__(callbacks=["handler"], metadata={"langfuse_session_id": "s"})

        def set_report(self, report):
            reports.append(report)

    @contextmanager
    def fake_trace(settings, **kw):
        yield Spy()

    _fake_stream(monkeypatch, plain, [], files={"main.py": "1"})
    monkeypatch.setattr(deps, "trace_run", fake_trace)
    from coding_agent.graph.state import FinalReport
    from coding_agent.llm import Usage

    def stream(graph, task, fixtures=None, config=None):
        received["config"] = config
        yield "finalize", {"final": FinalReport(
            success=True, files={}, explanation="ok", repairs=0, usage=Usage(1, 1))}

    monkeypatch.setattr("coding_agent.cli.stream_task", stream)
    assert runner.invoke(app, ["run", "t", "--out", str(tmp_path / "o")]).exit_code == 0
    assert received["config"]["callbacks"] == ["handler"]
    assert len(reports) == 1 and reports[0].success


def test_handler_creation_failure_does_not_break_the_run(monkeypatch, keyed, tmp_path):
    def boom(settings):
        raise RuntimeError("langfuse unreachable")

    _fake_stream(monkeypatch, keyed, [], files={"main.py": "1"})
    monkeypatch.setattr(langfuse_setup, "_new_client", boom)
    langfuse_setup.reset()
    result = runner.invoke(app, ["run", "t", "--out", str(tmp_path / "o")])
    assert result.exit_code == 0 and "SUCCESS" in result.output
    assert SECRET not in result.output


def test_eval_prints_the_line_passes_settings_and_flushes(monkeypatch, plain, flushes, tmp_path):
    captured = {}
    from coding_agent import cli

    real = cli.run_benchmark

    def spy(*a, **kw):
        captured.update(kw)
        return real(*a, **kw)

    monkeypatch.setattr(deps, "load_settings", lambda: plain)
    monkeypatch.setattr(deps, "tasks_dir", lambda: TASKS)
    monkeypatch.setattr(deps, "make_router", lambda s, t, all_strong=False: object())
    monkeypatch.setattr(deps, "make_sandbox", lambda s: GoodSandbox())
    monkeypatch.setattr(deps, "build_system", lambda *a, **k: ScriptedSystem())
    monkeypatch.setattr(cli, "run_benchmark", spy)
    result = runner.invoke(
        app, ["eval", "--system", "graph", "--subset", "full", "--out-dir", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert OFF in result.output
    assert captured["tracing"] is plain
    assert len(flushes) == 1


def test_eval_flushes_on_interrupt(monkeypatch, plain, flushes, tmp_path):
    from coding_agent import cli

    monkeypatch.setattr(deps, "load_settings", lambda: plain)
    monkeypatch.setattr(deps, "tasks_dir", lambda: TASKS)
    monkeypatch.setattr(deps, "make_router", lambda s, t, all_strong=False: object())
    monkeypatch.setattr(deps, "make_sandbox", lambda s: GoodSandbox())
    monkeypatch.setattr(deps, "build_system", lambda *a, **k: ScriptedSystem())

    def interrupted(*a, **kw):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "run_benchmark", interrupted)
    result = runner.invoke(
        app, ["eval", "--system", "graph", "--subset", "full", "--out-dir", str(tmp_path)])
    assert result.exit_code == 130 and len(flushes) == 1
