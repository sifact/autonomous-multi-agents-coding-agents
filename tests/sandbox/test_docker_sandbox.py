import subprocess

import pytest

from coding_agent.sandbox import DockerSandbox, Limits, write_files

pytestmark = pytest.mark.docker
IMAGE = "coding-agent-sandbox:latest"


@pytest.fixture
def sandbox():
    return DockerSandbox(IMAGE)


def test_hello_world(sandbox, workspace):
    write_files(workspace, {"main.py": "print('hello')"})
    r = sandbox.run(workspace, ["python", "main.py"])
    assert r.exit_code == 0 and r.stdout.strip() == "hello" and not r.timed_out


def test_nonzero_exit_captured_with_traceback(sandbox, workspace):
    write_files(workspace, {"main.py": "raise ValueError('bad')"})
    r = sandbox.run(workspace, ["python", "main.py"])
    assert r.exit_code != 0 and "Traceback" in r.stderr and "ValueError" in r.stderr


def test_runs_as_non_root(sandbox, workspace):
    r = sandbox.run(workspace, ["id", "-u"])
    assert r.stdout.strip() != "0"


def test_isolation_flags(sandbox, workspace):
    r = sandbox.run(workspace, ["sh", "-c", "touch /etc/x; echo $HOME $MPLCONFIGDIR; pwd"])
    assert r.exit_code == 0 or "Read-only" in r.stderr
    assert "Read-only" in r.stderr
    assert "/tmp /tmp/mpl" in r.stdout and "/workspace" in r.stdout


def test_timeout_kills_container_and_leaves_no_orphan(sandbox, workspace):
    r = sandbox.run(workspace, ["sleep", "60"], Limits(timeout_s=2))
    assert r.timed_out
    ps = subprocess.run(["docker", "ps", "-aq", "--filter", "name=coding-agent-"], capture_output=True, text=True)
    assert ps.stdout.strip() == ""


def test_files_written_in_workspace_visible_to_host(sandbox, workspace):
    write_files(workspace, {"main.py": "open('out.txt','w').write('hi')"})
    sandbox.run(workspace, ["python", "main.py"])
    assert (workspace / "out.txt").read_text() == "hi"


def test_disk_fill_is_stopped(sandbox, workspace):
    code = (
        "import os\n"
        "for i in range(10000):\n"
        "    open(f'f{i}','wb').write(os.urandom(1024*1024))\n"
    )
    write_files(workspace, {"main.py": code})
    r = sandbox.run(workspace, ["python", "main.py"], Limits(disk_mb=8, timeout_s=60))
    assert r.disk_exceeded
    total = sum(p.stat().st_size for p in workspace.iterdir())
    assert total < 200 * 1024 * 1024
