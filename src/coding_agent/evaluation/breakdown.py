"""Final-pass rate per task category and per difficulty, from the tasks' ``task.toml``."""
from collections import defaultdict
from pathlib import Path

from coding_agent.evaluation.results_io import ResultFile
from coding_agent.evaluation.task import load_tasks

UNKNOWN = "unknown"  # the record's task id is not in the task directory
UNSPECIFIED = "unspecified"


def _metadata(tasks_dir: Path | None) -> dict[str, tuple[str, str]] | None:
    """``task id -> (category, difficulty)``, or None when the tasks cannot be read."""
    if tasks_dir is None or not tasks_dir.is_dir():
        return None
    try:
        return {t.id: (t.category, t.difficulty or UNSPECIFIED) for t in load_tasks(tasks_dir)}
    except (OSError, ValueError):
        return None


def _table(title: str, column: str, rows: list[ResultFile], index: int,
           meta: dict[str, tuple[str, str]], labels: list[str]) -> list[str]:
    cells: dict[str, dict[int, list[bool]]] = defaultdict(lambda: defaultdict(list))
    for i, result in enumerate(rows):
        for rec in result.records:
            group = meta[rec.task_id][index] if rec.task_id in meta else UNKNOWN
            cells[group][i].append(rec.final_pass)
    out = [f"### {title}", "", "Final pass rate (runs in brackets).", "",
           "| " + " | ".join([column, *labels]) + " |",
           "|" + "---|" * (len(labels) + 1)]
    for group in sorted(cells):
        row = [group]
        for i in range(len(rows)):
            vals = cells[group].get(i)
            row.append(f"{sum(vals) / len(vals):.1%} ({len(vals)})" if vals else "n/a")
        out.append("| " + " | ".join(row) + " |")
    return out + [""]


def render_breakdown(rows: list[ResultFile], labels: list[str], tasks_dir: Path | None) -> str:
    """Markdown tables by category and difficulty, or a one-line skip note."""
    meta = _metadata(tasks_dir)
    if meta is None:
        return "Breakdown skipped: the task directory with task.toml metadata was not found."
    return "\n".join(
        _table("By category", "Category", rows, 0, meta, labels)
        + _table("By difficulty", "Difficulty", rows, 1, meta, labels)
    ).rstrip()
