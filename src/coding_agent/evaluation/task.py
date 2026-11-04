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
    )


def load_tasks(root: Path) -> list[Task]:
    """Load every task directory under root, sorted by id."""
    return [load_task(d) for d in sorted(root.iterdir()) if d.is_dir()]
