"""Adversarial programs the sandbox must contain, plus how to judge each one.

Each case is a task that tries to escape or exhaust the sandbox. `expect` judges
the ExecResult; `post_check` (optional) judges things only the host can see
(orphan containers, a canary file, free disk).
"""
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from coding_agent.sandbox import ExecResult, Limits

CONTAINER_PREFIX = "coding-agent-"
DISK_DELTA_LIMIT_MB = 200
DISK_MARGIN_MB = 96  # watcher poll + kill latency overshoot (observed up to ~60 MB)
CANARY_TOKEN = "__CANARY__"  # replaced with the host canary path before running
WORKSPACE_TOKEN = "__WORKSPACE__"  # replaced with the real host workspace path
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


def _disk_bounded(ctx: HostContext) -> bool:
    """Final workspace size stays near disk_mb; host free-space drop is a loose backstop."""
    size = sum(f.stat().st_size for f in ctx.workspace.rglob("*") if f.is_file())
    freed = ctx.free_bytes_before - shutil.disk_usage(ctx.workspace).free
    return size <= (_FAST.disk_mb + DISK_MARGIN_MB) * _MB and freed < DISK_DELTA_LIMIT_MB * _MB


# Children sleep so nothing runs away; the pids limit must stop forking long before 200.
_FORK_BOMB = """
import os, time
for _ in range(200):
    try:
        pid = os.fork()
    except OSError:
        print("LIMITED")
        break
    if pid == 0:
        time.sleep(3)
        os._exit(0)
else:
    print("UNBOUNDED")
"""

# Allocation is capped and touched (b"x"*n writes pages); only the memory limit can stop it.
_MEMORY_HOG = """
data = []
for _ in range(400):
    data.append(b"x" * (1 << 20))
print("ALLOCATED")
"""

_DELETE = f"""
import os, shutil
def writable(path):
    try:
        probe = os.path.join(path, ".probe")
        open(probe, "w").close()
        os.remove(probe)
        return True
    except OSError:
        return False
for target in ("/usr/bin/env", "/etc/hostname", "{CANARY_TOKEN}"):
    for fn in (os.remove, shutil.rmtree):
        try:
            fn(target)
        except Exception:
            pass
shutil.rmtree("/usr", ignore_errors=True)
print("SENTINEL_OK" if os.path.exists("/usr/bin/env") else "SENTINEL_GONE")
# Positive control: only /tmp and the workspace may be writable.
print("RO_ROOT" if not any(writable(p) for p in ("/usr", "/etc", "/")) else "RW_ROOT")
print("RW_OK" if writable("/tmp") and writable("/workspace") else "RW_BROKEN")
"""

_NETWORK = """
import os, socket
print("LO_ONLY" if sorted(os.listdir("/sys/class/net")) == ["lo"] else "HAS_NICS")
try:
    socket.create_connection(("1.1.1.1", 53), 2)
    print("CONNECTED")
except OSError:
    print("BLOCKED")
"""

# 8 MB files stay under the per-file fsize cap, so only the disk watcher can stop this.
_DISK_FILL = """
chunk = b"x" * (8 << 20)
i = 0
while True:
    with open(f"fill{i}.bin", "wb") as f:
        f.write(chunk)
    i += 1
"""

_READ_HOST = f"""
import os
visible = os.path.exists("{CANARY_TOKEN}") or os.path.exists("{WORKSPACE_TOKEN}")
print("HOST_VISIBLE" if visible else "ABSENT")
"""

SAFETY_CASES: list[SafetyCase] = [
    SafetyCase(
        "fork_bomb", _FORK_BOMB, lambda r: "LIMITED" in r.stdout and not r.timed_out,
        post_check=_no_orphans,
    ),
    SafetyCase("infinite_loop", "while True:\n    pass\n", lambda r: r.timed_out),
    SafetyCase(
        "memory_hog", _MEMORY_HOG,
        lambda r: "ALLOCATED" not in r.stdout
        and (r.oom_killed or (not r.timed_out and r.exit_code != 0)),
    ),
    SafetyCase(
        "delete_outside_workspace", _DELETE,
        lambda r: all(m in r.stdout for m in ("SENTINEL_OK", "RO_ROOT", "RW_OK")),
        post_check=_canary_intact,
    ),
    SafetyCase(
        "network_call", _NETWORK,
        lambda r: "BLOCKED" in r.stdout and "LO_ONLY" in r.stdout and "CONNECTED" not in r.stdout,
    ),
    SafetyCase(
        "disk_fill", _DISK_FILL,
        lambda r: r.disk_exceeded or (not r.timed_out and r.exit_code != 0),
        post_check=_disk_bounded,
    ),
    SafetyCase(
        "read_host_path", _READ_HOST,
        lambda r: "ABSENT" in r.stdout and "HOST_VISIBLE" not in r.stdout,
    ),
]
