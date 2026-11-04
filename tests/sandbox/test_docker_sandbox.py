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


def _probe(sandbox, workspace, code, limits=None):
    write_files(workspace, {"probe.py": code})
    return sandbox.run(workspace, ["python", "probe.py"], limits)


def test_read_only_root_and_env(sandbox, workspace):
    r = sandbox.run(workspace, ["sh", "-c", "touch /etc/x; echo $HOME $MPLCONFIGDIR; pwd"])
    assert "Read-only" in r.stderr
    assert "/tmp /tmp/mpl" in r.stdout and "/workspace" in r.stdout


def test_network_disabled_by_default(sandbox, workspace):
    code = "import socket; socket.create_connection(('1.1.1.1',53),2)"
    r = _probe(sandbox, workspace, code)
    assert r.exit_code != 0 and "Traceback" in r.stderr


def test_no_capabilities_and_no_new_privs(sandbox, workspace):
    code = "print(open('/proc/self/status').read())"
    r = _probe(sandbox, workspace, code)
    assert "CapEff:\t0000000000000000" in r.stdout
    assert "CapBnd:\t0000000000000000" in r.stdout  # fails without --cap-drop ALL
    assert "NoNewPrivs:\t1" in r.stdout


def test_uid_1000_and_cannot_write_root_owned(sandbox, workspace):
    code = (
        "import os\nprint(os.getuid(), os.getgid())\n"
        "open('/etc/x','w')"
    )
    r = _probe(sandbox, workspace, code)
    assert r.stdout.split() == ["1000", "1000"]
    assert "Errno" in r.stderr


def test_pids_limit_enforced(sandbox, workspace):
    code = (
        "import subprocess\nps=[]\n"
        "for i in range(60):\n"
        "    ps.append(subprocess.Popen(['sleep','5']))\n"
    )
    r = _probe(sandbox, workspace, code, Limits(pids=16, timeout_s=20))
    assert r.exit_code != 0 and ("BlockingIOError" in r.stderr or "Resource" in r.stderr)
    ps = subprocess.run(["docker", "ps", "-aq", "--filter", "name=coding-agent-"],
                        capture_output=True, text=True, check=False)
    assert ps.stdout.strip() == ""


def test_memory_limit_sets_oom_killed(sandbox, workspace):
    r = _probe(sandbox, workspace, "x = bytearray(400*1024*1024)\nx[::4096] = b'a'*len(x[::4096])",
               Limits(memory_mb=64))
    assert r.oom_killed and r.exit_code == 137


def test_normal_run_not_oom_killed(sandbox, workspace):
    assert not sandbox.run(workspace, ["true"]).oom_killed


def test_cpu_quota_matches_limits(sandbox, workspace):
    code = "print(open('/sys/fs/cgroup/cpu.max').read())"
    r = _probe(sandbox, workspace, code, Limits(cpus=0.5))
    assert r.stdout.split()[:2] == ["50000", "100000"]


def test_container_can_write_into_nested_dir_made_by_write_files(sandbox, workspace):
    write_files(workspace, {"pkg/sub/mod.py": "open('out.txt','w').write('ok')"})
    r = sandbox.run(workspace, ["sh", "-c", "cd pkg/sub && python mod.py"])
    assert r.exit_code == 0, r.stderr
    assert (workspace / "pkg" / "sub" / "out.txt").read_text() == "ok"


def test_timeout_kills_container_and_leaves_no_orphan(sandbox, workspace):
    r = sandbox.run(workspace, ["sleep", "60"], Limits(timeout_s=2))
    assert r.timed_out
    ps = subprocess.run(["docker", "ps", "-aq", "--filter", "name=coding-agent-"], capture_output=True, text=True, check=False)
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


def test_run_command_pins_user_explicitly(sandbox, workspace):
    """The image already sets USER 1000, so the flag is checked on the argv."""
    args = sandbox._docker_args("n", workspace, Limits(), ["true"])
    assert args[args.index("--user") + 1] == "1000:1000"
