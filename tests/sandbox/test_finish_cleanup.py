import subprocess

import pytest

from coding_agent.sandbox import docker_sandbox
from coding_agent.sandbox.docker_sandbox import DockerSandbox


@pytest.mark.parametrize("failing", ["kill", "inspect"])
def test_finish_removes_container_even_if_kill_or_inspect_raises(monkeypatch, failing):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args[1])
        if args[1] == failing:
            raise subprocess.TimeoutExpired(args, 30)
        return subprocess.CompletedProcess(args, 0, stdout="false\n", stderr="")

    monkeypatch.setattr(docker_sandbox.subprocess, "run", fake_run)
    with pytest.raises(subprocess.TimeoutExpired):
        DockerSandbox._finish("coding-agent-x")
    assert "rm" in calls
