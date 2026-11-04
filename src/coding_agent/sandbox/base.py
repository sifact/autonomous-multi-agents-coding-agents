"""Sandbox contract shared by every executor backend."""
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from coding_agent.sandbox.limits import Limits


@dataclass(frozen=True)
class ExecResult:
    """Outcome of one sandboxed command."""

    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    oom_killed: bool
    duration_s: float
    # Set when the workspace grew past Limits.disk_mb and the run was killed.
    disk_exceeded: bool = False


class Sandbox(Protocol):
    """Anything that can run a command against a workspace under limits."""

    def run(self, workspace: Path, command: list[str], limits: Limits | None = None) -> ExecResult:
        ...
