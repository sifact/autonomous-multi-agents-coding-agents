"""Workspace helpers: unique dirs, safe file writes, output truncation."""
import tempfile
from pathlib import Path


class PathEscapeError(ValueError):
    """Raised when a file path would land outside the workspace."""


def make_workspace(root: Path | None = None) -> Path:
    """Create a unique workspace dir under the shared workspace root.

    Lives under $HOME by default because Colima only bind-mounts $HOME.
    """
    if root is None:
        from coding_agent.config import get_settings  # lazy: config imports sandbox

        root = get_settings().workspace_root
    root.mkdir(parents=True, exist_ok=True)
    path = Path(tempfile.mkdtemp(prefix="ws-", dir=root))
    path.chmod(0o777)  # container user (uid 1000) must be able to write
    return path


def _make_dirs(base: Path, directory: Path) -> None:
    """mkdir -p, making each new dir world-writable (umask would give 0755)."""
    missing = []
    d = directory
    while d != base and not d.exists():
        missing.append(d)
        d = d.parent
    for d in reversed(missing):
        d.mkdir()
        d.chmod(0o777)


def write_files(workspace: Path, files: dict[str, str]) -> None:
    """Write files into the workspace, refusing absolute or escaping paths."""
    base = workspace.resolve()
    targets: list[tuple[Path, str]] = []
    for rel, content in files.items():
        if Path(rel).is_absolute() or ".." in Path(rel).parts:
            raise PathEscapeError(f"path escapes workspace: {rel!r}")
        target = (base / rel).resolve()
        if not target.is_relative_to(base):
            raise PathEscapeError(f"path escapes workspace: {rel!r}")
        targets.append((target, content))
    for target, content in targets:
        _make_dirs(base, target.parent)
        target.write_text(content)
        target.chmod(0o666)


def truncate(text: str, max_chars: int = 20_000) -> str:
    """Cut long output (keeping head and tail) and mark that it was cut."""
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    cut = len(text) - 2 * half
    return f"{text[:half]}\n...[truncated {cut} chars]...\n{text[-half:]}"
