"""Read benchmark result files back into typed objects for the report.

Why recompute metrics: the report must agree with the records it shows, so the
stored ``metrics`` block is ignored and ``aggregate`` runs over the records.
A valid JSON file that is not result-shaped (no ``system`` and ``records`` keys)
is not ours and is skipped silently; a result-shaped file that is broken is
skipped with a warning so a bad file never hides behind a good table.
"""
import json
import warnings
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field, fields
from datetime import datetime
from pathlib import Path
from typing import Any

from coding_agent.evaluation.metrics import Metrics, RunRecord, aggregate

DEFAULT_VARIANT = "full"
SYSTEM_ORDER = ("single_shot", "single_agent", "graph")
VARIANT_LABELS = {
    "no-planner": "no planner", "no-architect": "no architect", "all-strong": "all strong",
}
_RECORD_FIELDS = {f.name for f in fields(RunRecord)}


class ResultFileWarning(UserWarning):
    """A result file was skipped because it is malformed."""


@dataclass(frozen=True)
class ResultFile:
    """One benchmark run as saved by the runner."""

    path: Path
    system: str
    variant: str
    timestamp: datetime
    git_sha: str | None
    git_dirty: bool | None
    models: dict[str, str]
    resolved_roles: dict[str, str]
    settings: dict[str, Any]
    budget_note: str
    seed: int | None
    repeats: int | None
    task_ids: list[str]
    records: list[RunRecord]
    metrics: Metrics = field(compare=False)

    @property
    def label(self) -> str:
        return variant_label(self.system, self.variant)

    @property
    def sort_key(self) -> tuple[int, str, str]:
        return sort_key(self.system, self.variant) + (self.timestamp.isoformat(),)


def variant_label(system: str, variant: str) -> str:
    """``graph`` for the full graph, ``graph (no planner)`` for an ablation."""
    if variant == DEFAULT_VARIANT:
        return system
    return f"{system} ({VARIANT_LABELS.get(variant, variant)})"


def sort_key(system: str, variant: str) -> tuple[int, str]:
    """single_shot, single_agent, graph, graph variants A-Z, then anything else."""
    rank = SYSTEM_ORDER.index(system) if system in SYSTEM_ORDER else len(SYSTEM_ORDER)
    return (rank, "" if variant == DEFAULT_VARIANT else variant) if rank < 3 else (
        rank, f"{system}/{variant}")


def _record(raw: Any) -> RunRecord:
    if not isinstance(raw, dict):
        raise TypeError("a record is not an object")
    return RunRecord(**{k: v for k, v in raw.items() if k in _RECORD_FIELDS})


def _parse(path: Path, data: dict[str, Any]) -> ResultFile:
    if not isinstance(data["system"], str) or not isinstance(data["records"], list):
        raise TypeError("'system' must be a string and 'records' a list")
    if not data["records"]:
        raise ValueError("no records")
    timestamp = datetime.fromisoformat(str(data["timestamp"]))
    if timestamp.tzinfo is None:
        raise ValueError("timestamp has no timezone offset, so it cannot be ordered")
    records = [_record(r) for r in data["records"]]
    return ResultFile(
        path=path, system=data["system"], variant=data.get("variant") or DEFAULT_VARIANT,
        timestamp=timestamp, git_sha=data.get("git_sha"), git_dirty=data.get("git_dirty"),
        models=dict(data.get("models") or {}),
        resolved_roles=dict(data.get("resolved_roles") or {}),
        settings=dict(data.get("settings") or {}), budget_note=str(data.get("budget_note") or ""),
        seed=data.get("seed"), repeats=data.get("repeats"),
        task_ids=list(data.get("task_ids") or []), records=records, metrics=aggregate(records),
    )


def _files(source: Path | str | Iterable[Path | str]) -> list[Path]:
    items = [source] if isinstance(source, (str, Path)) else list(source)
    out: list[Path] = []
    for item in items:
        p = Path(item)
        out.extend(sorted(p.glob("*.json")) if p.is_dir() else [p])
    return out


def load_results(
    source: Path | str | Iterable[Path | str], on_warning: Callable[[str], None] | None = None,
) -> list[ResultFile]:
    """Load result files from a directory or a list of paths; skip the unusable ones."""
    def warn(message: str) -> None:
        if on_warning:
            on_warning(message)
        else:
            warnings.warn(message, ResultFileWarning, stacklevel=3)

    loaded: list[ResultFile] = []
    for path in _files(source):
        try:
            data = json.loads(path.read_text())
        except OSError as exc:
            warn(f"Skipped {path}: cannot read it ({exc.strerror or exc})")
            continue
        except ValueError as exc:
            warn(f"Skipped {path}: not valid JSON ({exc})")
            continue
        if not isinstance(data, dict) or not {"system", "records"} <= data.keys():
            continue  # some other JSON file, not a benchmark result
        try:
            loaded.append(_parse(path, data))
        except (ValueError, TypeError, KeyError) as exc:
            warn(f"Skipped {path}: malformed result file ({type(exc).__name__}: {exc})")
    return loaded


def select_latest(results: list[ResultFile]) -> list[ResultFile]:
    """The newest file per (system, variant), in report order."""
    newest: dict[tuple[str, str], ResultFile] = {}
    for r in results:
        key = (r.system, r.variant)
        if key not in newest or r.timestamp > newest[key].timestamp:
            newest[key] = r
    return sorted(newest.values(), key=lambda r: r.sort_key)
