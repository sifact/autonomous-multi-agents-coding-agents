"""Resource limits applied to every sandbox container."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Limits:
    """Caps that keep generated code from exhausting the host."""

    memory_mb: int = 512
    cpus: float = 1.0
    timeout_s: int = 30
    pids: int = 64
    disk_mb: int = 64
    network: bool = False
