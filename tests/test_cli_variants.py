"""`agent eval --variant`: the choice reaches the system and the result file."""
import json

import pytest
from typer.testing import CliRunner

from coding_agent.cli import app
from coding_agent.cli_support import deps
from coding_agent.config import Settings
from coding_agent.sandbox import ExecResult
from tests.evaluation.helpers import TASKS
from tests.graph.fakes import code, layout, scripted_router, verdict
from tests.test_cli import ScriptedSystem

runner = CliRunner()


class GoodSandbox:
    def run(self, workspace, command, limits=None):
        return ExecResult(0, "1 passed", "", False, False, 0.1)


@pytest.fixture
def settings():
    return Settings(groq_api_key="test-key", _env_file=None)


@pytest.fixture
def captured(monkeypatch, settings):
    seen = {}

    def build(name, s, sandbox, all_strong=False, variant="full"):
        seen.update(name=name, all_strong=all_strong, variant=variant)
        return ScriptedSystem()

    monkeypatch.setattr(deps, "load_settings", lambda: settings)
    monkeypatch.setattr(deps, "tasks_dir", lambda: TASKS)
    monkeypatch.setattr(deps, "make_sandbox", lambda s: GoodSandbox())
    monkeypatch.setattr(deps, "make_router", lambda s, t, all_strong=False: object())
    monkeypatch.setattr(deps, "build_system", build)
    return seen


def _eval(tmp_path, *extra, system="graph"):
    return runner.invoke(app, [
        "eval", "--system", system, "--subset", "full", "--out-dir", str(tmp_path), *extra])


@pytest.mark.parametrize("variant", ["full", "no-planner", "no-architect", "all-strong"])
def test_variant_reaches_build_system(captured, tmp_path, variant):
    result = _eval(tmp_path, "--variant", variant)
    assert result.exit_code == 0, result.output
    assert captured["variant"] == variant and captured["name"] == "graph"
    assert captured["all_strong"] is (variant == "all-strong")


def test_all_strong_flag_is_the_all_strong_variant(captured, tmp_path):
    assert _eval(tmp_path, "--all-strong").exit_code == 0
    assert captured["variant"] == "all-strong" and captured["all_strong"] is True


def test_all_strong_flag_with_the_all_strong_variant_is_fine(captured, tmp_path):
    assert _eval(tmp_path, "--all-strong", "--variant", "all-strong").exit_code == 0
    assert captured["variant"] == "all-strong"


def test_all_strong_cannot_combine_with_an_ablation(captured, tmp_path):
    result = _eval(tmp_path, "--all-strong", "--variant", "no-planner")
    assert result.exit_code == 2 and "cannot be combined" in result.output
    assert not captured


def test_variant_other_than_full_is_graph_only(captured, tmp_path):
    result = _eval(tmp_path, "--variant", "no-planner", system="single_agent")
    assert result.exit_code == 2 and "graph only" in result.output
    assert not captured


def test_unknown_variant_is_bad_input(captured, tmp_path):
    assert _eval(tmp_path, "--variant", "nope").exit_code == 2


def test_help_documents_variants():
    out = runner.invoke(app, ["eval", "--help"]).output
    assert "--variant" in out and "no-planner" in out


def test_real_wiring_writes_a_variant_named_result_file(monkeypatch, settings, tmp_path):
    """Real build_system + GraphSystem + build_graph with scripted models, no planner call."""
    routers = []

    def make_router(s, tracker, all_strong=False):
        router, llms = scripted_router(
            s, tracker, architect=[layout()], coder=[code("print('ok')")],
            reviewer=[verdict("pass")])
        routers.append(llms)
        return router

    monkeypatch.setattr(deps, "load_settings", lambda: settings)
    monkeypatch.setattr(deps, "tasks_dir", lambda: TASKS)
    monkeypatch.setattr(deps, "make_sandbox", lambda s: GoodSandbox())
    monkeypatch.setattr(deps, "make_router", make_router)
    result = _eval(tmp_path, "--variant", "no-planner")
    assert result.exit_code == 0, result.output
    (path,) = tmp_path.glob("graph-no-planner-*.json")
    data = json.loads(path.read_text())
    assert data["variant"] == "no-planner" and data["system"] == "graph"
    assert data["resolved_roles"]["planner"] == "skipped"
    assert data["resolved_roles"]["architect"] == "fake-architect"
    assert len(data["records"]) == 2 and all(r["error"] is None for r in data["records"])
    assert len(routers) == 3  # the early key check, then one router per task
    assert all(llms["planner"].calls == [] for llms in routers[1:])
    assert "graph (no planner)" in result.output
    report = runner.invoke(app, ["report", "--results-dir", str(tmp_path)])
    assert report.exit_code == 0 and "| graph (no planner) | 2 | 2 |" in report.output
