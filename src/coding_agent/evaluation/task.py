"""Eval task format and on-disk loader."""
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Task:
    """One benchmark task: a prompt, hidden tests, and optional starting code."""

    id: str
    category: str
    prompt: str
    fixtures: dict[str, str]
    hidden_tests: dict[str, str]
    starter: dict[str, str] | None
    reference: dict[str, str]
    difficulty: str | None = None


def _read_tree(directory: Path) -> dict[str, str]:
    """Map relative posix path -> text for every file under directory."""
    return {
        p.relative_to(directory).as_posix(): p.read_text()
        for p in sorted(directory.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
    }


def load_task(task_dir: Path) -> Task:
    """Load one task directory, failing loudly on a malformed layout."""
    prompt_file = task_dir / "prompt.md"
    if not prompt_file.is_file():
        raise ValueError(f"task {task_dir.name}: missing prompt.md")
    hidden_dir = task_dir / "hidden_tests"
    if not hidden_dir.is_dir() or not any(hidden_dir.rglob("*.py")):
        raise ValueError(f"task {task_dir.name}: missing hidden_tests/")
    meta_file = task_dir / "task.toml"
    meta = tomllib.loads(meta_file.read_text()) if meta_file.is_file() else {}
    starter_dir = task_dir / "starter"
    return Task(
        id=task_dir.name,
        category=meta.get("category", "uncategorized"),
        prompt=prompt_file.read_text(),
        fixtures=_read_tree(task_dir / "fixtures") if (task_dir / "fixtures").is_dir() else {},
        hidden_tests=_read_tree(hidden_dir),
        starter=_read_tree(starter_dir) if starter_dir.is_dir() else None,
        reference=_read_tree(task_dir / "reference") if (task_dir / "reference").is_dir() else {},
        difficulty=meta.get("difficulty"),
    )


def load_tasks(root: Path) -> list[Task]:
    """Load every task directory under root, sorted by id (skips dirs starting with '.' or '_')."""
    dirs = sorted(
        d for d in root.iterdir() if d.is_dir() and not d.name.startswith((".", "_"))
    )
    return [load_task(d) for d in dirs]


def load_fast_subset(root: Path, subset_file: Path | None = None) -> list[Task]:
    """Load the tasks named in the fast-subset list, in the order listed.

    The list defaults to ``fast_subset.txt`` next to the tasks directory: one task id per
    line, blank lines and ``#`` comment lines ignored. An unknown or repeated id is an error,
    so the quick CI run cannot silently shrink.
    """
    path = subset_file if subset_file is not None else root.parent / "fast_subset.txt"
    ids = [
        line.strip() for line in path.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path.name}: duplicate task ids")
    missing = [i for i in ids if not (root / i).is_dir()]
    if missing:
        raise ValueError(f"{path.name}: unknown task ids: {', '.join(missing)}")
    return [load_task(root / i) for i in ids]
