"""Docker-backed sandbox: runs a command in a locked-down throwaway container.

Disk cap choice: the workspace is a bind mount (so files are visible to the host
without copying). A size-capped tmpfs workspace was rejected because tmpfs is
mounted only at container start, so files could not be copied in/out cleanly.
Instead disk_mb is enforced three ways: `--ulimit fsize` caps any single file,
a host-side watcher polls the workspace size during the run and kills the
container once it exceeds disk_mb, and the size is re-checked after the run.
"""
import os
import subprocess
import threading
import time
import uuid
from pathlib import Path

from coding_agent.sandbox.base import ExecResult
from coding_agent.sandbox.limits import Limits

POLL_INTERVAL_S = 0.1
_MB = 1024 * 1024


def _dir_size(path: Path) -> int:
    total = 0
    for dirpath, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.lstat(os.path.join(dirpath, name)).st_size
            except OSError:
                pass
    return total


class DockerSandbox:
    """Executes commands via the docker CLI with strict isolation flags."""

    def __init__(self, image: str) -> None:
        self.image = image

    def _docker_args(self, name: str, workspace: Path, limits: Limits, command: list[str]) -> list[str]:
        args = [
            "docker", "run", "--name", name,
            "--user", "1000:1000",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "--read-only",
            "--tmpfs", "/tmp:rw,size=64m,mode=1777",
            "--memory", f"{limits.memory_mb}m",
            "--memory-swap", f"{limits.memory_mb}m",
            "--cpus", str(limits.cpus),
            "--pids-limit", str(limits.pids),
            "--ulimit", f"fsize={limits.disk_mb * _MB}:{limits.disk_mb * _MB}",
            "-e", "MPLCONFIGDIR=/tmp/mpl",
            "-e", "HOME=/tmp",
            "-v", f"{workspace.resolve()}:/workspace",
            "-w", "/workspace",
        ]
        if not limits.network:
            args += ["--network", "none"]
        return args + [self.image, *command]

    @staticmethod
    def _kill(name: str) -> None:
        subprocess.run(["docker", "kill", name], capture_output=True, timeout=30, check=False)

    @staticmethod
    def _finish(name: str) -> bool:
        """Kill if still running, read State.OOMKilled, then remove the container.

        --rm is not used so the OOM flag can be inspected before removal; the
        exit code 137 alone cannot tell OOM from a manual kill.
        """
        subprocess.run(["docker", "kill", name], capture_output=True, timeout=30, check=False)
        insp = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.OOMKilled}}", name],
            capture_output=True, text=True, timeout=30, check=False,
        )
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=30, check=False)
        return insp.stdout.strip() == "true"

    def run(self, workspace: Path, command: list[str], limits: Limits | None = None) -> ExecResult:
        limits = limits or Limits()
        name = f"coding-agent-{uuid.uuid4().hex[:12]}"
        args = self._docker_args(name, workspace, limits, command)
        start = time.monotonic()
        stop = threading.Event()
        disk_exceeded = threading.Event()

        def watch_disk() -> None:
            while not stop.wait(POLL_INTERVAL_S):
                if _dir_size(workspace) > limits.disk_mb * _MB:
                    disk_exceeded.set()
                    self._kill(name)
                    return

        watcher = threading.Thread(target=watch_disk, daemon=True)
        watcher.start()
        timed_out = False
        oom = False
        try:
            proc = subprocess.run(
                args, capture_output=True, text=True, errors="replace", timeout=limits.timeout_s,
                check=False,
            )
            code, out, err = proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            code = 124
            out = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            err = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        finally:
            stop.set()
            watcher.join()
            oom = self._finish(name)  # guarantees no orphan, even on timeout or error
        if _dir_size(workspace) > limits.disk_mb * _MB:
            disk_exceeded.set()
        return ExecResult(
            exit_code=code,
            stdout=out,
            stderr=err,
            timed_out=timed_out,
            oom_killed=oom,
            duration_s=time.monotonic() - start,
            disk_exceeded=disk_exceeded.is_set(),
        )
