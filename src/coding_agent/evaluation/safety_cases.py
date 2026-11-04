"""Adversarial programs the sandbox must contain, plus how to judge each one.

Each case is a task that tries to escape or exhaust the sandbox. `expect` judges
the ExecResult; `post_check` (optional) judges things only the host can see
(orphan containers, a canary file, free disk).
"""
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from coding_agent.sandbox import ExecResult, Limits

CONTAINER_PREFIX = "coding-agent-"
DISK_DELTA_LIMIT_MB = 200
CANARY_TOKEN = "__CANARY__"  # replaced with the host canary path before running
_MB = 1024 * 1024
# Small limits keep the whole suite fast.
_FAST = Limits(timeout_s=5, memory_mb=64, pids=32, disk_mb=32)


@dataclass(frozen=True)
class HostContext:
    """Host-side state captured before a case runs."""

    workspace: Path
    canary: Path
    free_bytes_before: int
    containers_before: frozenset[str]


def list_agent_containers() -> frozenset[str]:
    """Names of coding-agent-* containers (running or not); ignores unrelated ones."""
    out = subprocess.run(
        ["docker", "ps", "-a", "--filter", f"name={CONTAINER_PREFIX}", "--format", "{{.Names}}"],
        capture_output=True, text=True, timeout=30, check=False,
    ).stdout
    return frozenset(n for n in out.split() if n.startswith(CONTAINER_PREFIX))


@dataclass(frozen=True)
class SafetyCase:
    name: str
    code: str
    expect: Callable[[ExecResult], bool]
    limits: Limits = _FAST
    post_check: Callable[[HostContext], bool] | None = field(default=None)


def _no_orphans(ctx: HostContext) -> bool:
    return not (list_agent_containers() - ctx.containers_before)


def _canary_intact(ctx: HostContext) -> bool:
    return ctx.canary.exists() and ctx.canary.read_text() == "alive"


def _disk_delta_small(ctx: HostContext) -> bool:
    import shutil
    freed = ctx.free_bytes_before - shutil.disk_usage(ctx.workspace).free
    return freed < DISK_DELTA_LIMIT_MB * _MB


_FORK_BOMB = """
import os
while True:
    try:
        os.fork()
    except OSError:
        pass
"""

_DELETE = f"""
import os, shutil
for target in ("/usr/bin/env", "/etc/hostname", "{CANARY_TOKEN}"):
    for fn in (os.remove, shutil.rmtree):
        try:
            fn(target)
        except Exception:
            pass
shutil.rmtree("/usr", ignore_errors=True)
print("SENTINEL_OK" if os.path.exists("/usr/bin/env") else "SENTINEL_GONE")
"""

_NETWORK = """
import socket
try:
    socket.create_connection(("1.1.1.1", 53), 2)
    print("CONNECTED")
except OSError:
    print("BLOCKED")
"""

_DISK_FILL = """
chunk = b"x" * (1 << 20)
with open("fill.bin", "wb") as f:
    while True:
        f.write(chunk)
        f.flush()
"""

_READ_HOST = """
import os
print("HOST_VISIBLE" if os.path.exists("/Users") else "ABSENT")
"""

SAFETY_CASES: list[SafetyCase] = [
    SafetyCase("fork_bomb", _FORK_BOMB, lambda r: r.duration_s < 20, post_check=_no_orphans),
    SafetyCase("infinite_loop", "while True:\n    pass\n", lambda r: r.timed_out),
    SafetyCase(
        "memory_hog", "data = []\nwhile True:\n    data.append(bytearray(1 << 20))\n",
        lambda r: r.oom_killed or r.exit_code != 0,
    ),
    SafetyCase(
        "delete_outside_workspace", _DELETE,
        lambda r: "SENTINEL_OK" in r.stdout, post_check=_canary_intact,
    ),
    SafetyCase(
        "network_call", _NETWORK, lambda r: "BLOCKED" in r.stdout and "CONNECTED" not in r.stdout,
    ),
    SafetyCase(
        "disk_fill", _DISK_FILL, lambda r: r.disk_exceeded or r.exit_code != 0,
        post_check=_disk_delta_small,
    ),
    SafetyCase("read_host_path", _READ_HOST, lambda r: "ABSENT" in r.stdout),
]
