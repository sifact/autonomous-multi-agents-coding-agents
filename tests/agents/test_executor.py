from pathlib import Path

import pytest

from coding_agent.agents import make_executor
from coding_agent.config import Settings
from coding_agent.sandbox import ExecResult

TEN_MB = 10 * 1024 * 1024


class RecordingSandbox:
    def __init__(self, result: ExecResult | None = None):
        self.result = result or ExecResult(0, "ok\n", "", False, False, 0.1)
        self.calls: list[tuple[Path, list[str], set[str]]] = []

    def run(self, workspace, command, limits=None):
        seen = {str(p.relative_to(workspace)) for p in workspace.rglob("*") if p.is_file()}
        self.calls.append((workspace, command, seen))
        self.limits = limits
        return self.result


@pytest.fixture
def settings(tmp_path):
    return Settings(workspace_root=tmp_path / "ws")


def test_runs_main_records_version_and_cleans_up(state, settings):
    sb = RecordingSandbox()
    state["files"] = {"main.py": "print('ok')"}
    update = make_executor(sb, settings)(state)
    (ws, cmd, seen), = sb.calls
    assert cmd == ["python", "main.py"] and seen == {"main.py"}
    assert sb.limits == settings.limits
    assert not ws.exists()  # workspace removed afterwards
    assert update["last_exec"].exit_code == 0
    v = update["code_versions"][-1]
    assert v["version"] == 1 and v["files"] == {"main.py": "print('ok')"} and v["exit_code"] == 0
    assert update["visits"] == state["visits"] + 1
    assert not {"repairs", "replans", "verdict"} & update.keys()  # increments nothing
    assert update["events"][0]["node"] == "executor"


def test_appends_to_existing_versions(reviewed_state, settings):
    update = make_executor(RecordingSandbox(), settings)(reviewed_state)
    assert [v["version"] for v in update["code_versions"]] == [1, 2]


def test_tests_present_runs_pytest(state, settings):
    sb = RecordingSandbox()
    state["files"] = {"main.py": "x = 1", "tests/test_main.py": "def test_x(): pass"}
    make_executor(sb, settings)(state)
    assert sb.calls[0][1] == ["python", "-m", "pytest", "-q"]


def test_policy_hit_is_flagged(state, settings):
    state["files"] = {"main.py": "import os\nos.system('rm -rf /')\n", "notes.txt": "os.system"}
    update = make_executor(RecordingSandbox(), settings)(state)
    flags = update["code_versions"][-1]["flags"]
    assert {"path": "main.py", "rule": "shell_exec", "line": 2} in flags
    assert all(f["path"] == "main.py" for f in flags)  # only .py files are scanned
    assert update["events"][0]["flags"] == flags


def test_ten_mb_output_is_truncated(state, settings):
    big = ExecResult(0, "x" * TEN_MB, "e" * TEN_MB, False, False, 1.0)
    state["files"] = {"main.py": "print('x' * 10_000_000)"}
    update = make_executor(RecordingSandbox(big), settings)(state)
    r = update["last_exec"]
    assert len(r.stdout) < 20_100 and len(r.stderr) < 20_100
    assert "[truncated" in r.stdout and "[truncated" in r.stderr


def test_path_escape_is_an_execution_failure_not_a_crash(state, settings):
    sb = RecordingSandbox()
    state["files"] = {"../evil.py": "print('x')", "main.py": "print(1)"}
    update = make_executor(sb, settings)(state)
    assert sb.calls == []
    r = update["last_exec"]
    assert r.exit_code != 0 and "escapes workspace" in r.stderr
    assert update["code_versions"][-1]["exit_code"] == r.exit_code
    assert list((settings.workspace_root).iterdir()) == []  # cleaned up


def test_no_files_is_an_execution_failure(state, settings):
    sb = RecordingSandbox()
    update = make_executor(sb, settings)(state)
    assert sb.calls == [] and update["last_exec"].exit_code != 0
    assert "no files" in update["last_exec"].stderr.lower()


def test_no_entrypoint_compiles_modules(state, settings):
    sb = RecordingSandbox()
    state["files"] = {"stats.py": "def mean(x): return sum(x) / len(x)"}
    make_executor(sb, settings)(state)
    assert sb.calls[0][1] == ["python", "-m", "py_compile", "stats.py"]


@pytest.mark.parametrize("files", [
    {"main.py": "print(1)", "": "x"},
    {"main.py": "print(1)", ".": "x"},
    {"main.py": "print(1)", "pkg": "x", "pkg/a.py": "y"},
    {"main.py": "print(1)", "pkg/a.py": "y", "pkg": "x"},
], ids=["empty", "dot", "file-then-dir", "dir-then-file"])
def test_bad_model_paths_are_execution_failures(state, settings, files):
    sb = RecordingSandbox()
    state["files"] = files
    update = make_executor(sb, settings)(state)  # must not raise
    assert sb.calls == []
    r = update["last_exec"]
    assert r.exit_code != 0 and "could not write" in r.stderr.lower()
    assert list(settings.workspace_root.iterdir()) == []


def test_infrastructure_errors_propagate(state, settings):
    class Broken:
        def run(self, workspace, command, limits=None):
            raise FileNotFoundError("docker")

    state["files"] = {"main.py": "print(1)"}
    with pytest.raises(FileNotFoundError):
        make_executor(Broken(), settings)(state)
    assert list(settings.workspace_root.iterdir()) == []


def test_disk_exceeded_recorded(state, settings):
    r = ExecResult(137, "", "", False, False, 1.0, disk_exceeded=True)
    state["files"] = {"main.py": "print(1)"}
    update = make_executor(RecordingSandbox(r), settings)(state)
    assert update["code_versions"][-1]["disk_exceeded"] is True
