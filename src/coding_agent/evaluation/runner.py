"""Benchmark runner: solve each task, grade with the HIDDEN tests, record, save.

Reproducibility: Python's ``random`` is seeded with ``seed`` before every run.
The LLM itself is NOT seeded (providers do not guarantee determinism), so
repeats will differ; use ``repeats`` to see the spread.

Grading: ``final_pass`` grades the system's final files. ``first_try_pass`` grades
``SystemOutput.first_files`` (the attempt-1 files), so a system that crashed then
repaired is judged on its first output, not the repaired one. When the first and
final files are identical the single grade is reused (no second sandbox run).

Failures: an exception in one task becomes a failed record (``error`` set) and the
benchmark continues. After 3 consecutive such failures the last exception is
re-raised (infrastructure such as Docker being down would otherwise silently
produce a file full of zeros); results gathered so far are saved first.
"""
import dataclasses
import json
import random
import subprocess
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from coding_agent.evaluation.grader import grade
from coding_agent.evaluation.metrics import RunRecord, aggregate
from coding_agent.evaluation.systems import System, SystemOutput
from coding_agent.evaluation.task import Task
from coding_agent.sandbox import Sandbox

DEFAULT_OUT_DIR = Path("benchmarks/results")
MAX_CONSECUTIVE_FAILURES = 3
_sleep = time.sleep  # patched in tests


def git_sha() -> str | None:
    """HEAD commit of the current repo, or None when git or the repo is unavailable."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    sha = proc.stdout.strip()
    return sha if proc.returncode == 0 and sha else None


def _grade_record(task: Task, system_name: str, out: SystemOutput, sandbox: Sandbox) -> RunRecord:
    final = grade(task, out.files, sandbox)
    if out.first_files is None or out.first_files == out.files:
        first_pass = final.passed
    else:
        first_pass = grade(task, out.first_files, sandbox).passed
    return RunRecord(
        task_id=task.id, system=system_name, first_try_pass=first_pass, final_pass=final.passed,
        had_runtime_error=out.had_runtime_error, fixed_within_3=out.fixed, attempts=out.attempts,
        tokens_in=out.usage.tokens_in, tokens_out=out.usage.tokens_out, cost_usd=out.cost_usd,
        wall_s=out.wall_s, error=out.error,
    )


def _crash_record(task: Task, system_name: str, exc: Exception, wall_s: float) -> RunRecord:
    return RunRecord(
        task_id=task.id, system=system_name, first_try_pass=False, final_pass=False,
        had_runtime_error=False, fixed_within_3=False, attempts=0, tokens_in=0, tokens_out=0,
        cost_usd=None, wall_s=wall_s, error=f"{type(exc).__name__}: {exc}",
    )


def save_results(
    out_dir: Path, system: System, records: list[RunRecord], tasks: list[Task], *,
    seed: int, repeats: int, max_rpm: int | None, timestamp: datetime,
) -> Path:
    """Write ``<out_dir>/<system>-<timestamp>.json`` and return its path (None -> null)."""
    info = system.describe()
    payload: dict[str, Any] = {
        "system": system.name,
        "models": info.get("models", {}),
        "settings": info.get("settings", {}),
        "seed": seed,
        "repeats": repeats,
        "max_rpm": max_rpm,
        "git_sha": git_sha(),
        "timestamp": timestamp.isoformat(),
        "task_ids": [t.id for t in tasks],
        "records": [dataclasses.asdict(r) for r in records],
        "metrics": dataclasses.asdict(aggregate(records)) if records else None,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{system.name}-{timestamp.strftime('%Y%m%dT%H%M%SZ')}.json"
    path.write_text(json.dumps(payload, indent=2))
    return path


def run_benchmark(
    tasks: list[Task], system: System, sandbox: Sandbox, repeats: int = 1, seed: int = 0,
    max_rpm: int | None = None, out_dir: Path | None = None,
    on_record: Callable[[RunRecord], None] | None = None,
) -> list[RunRecord]:
    """Run ``system`` over ``tasks`` x ``repeats``, grade with hidden tests, save, return records.

    ``max_rpm`` is coarse pacing: run starts are spaced at least ``60 / max_rpm``
    seconds apart. The per-request limiter lives in the Groq client; this only
    keeps a benchmark of many quick tasks from bursting.
    """
    started = datetime.now(UTC)
    records: list[RunRecord] = []
    failures = 0
    last_exc: Exception | None = None
    last_start: float | None = None
    try:
        for _ in range(repeats):
            for task in tasks:
                if max_rpm and last_start is not None:
                    wait = 60 / max_rpm - (time.monotonic() - last_start)
                    if wait > 0:
                        _sleep(wait)
                last_start = time.monotonic()
                random.seed(seed)
                try:
                    record = _grade_record(task, system.name, system.solve(task), sandbox)
                    failures = 0
                except Exception as exc:  # noqa: BLE001 - one task must not kill the benchmark
                    record = _crash_record(task, system.name, exc, time.monotonic() - last_start)
                    failures, last_exc = failures + 1, exc
                records.append(record)
                if on_record:
                    on_record(record)
                if failures >= MAX_CONSECUTIVE_FAILURES:
                    assert last_exc is not None
                    raise last_exc
    finally:
        save_results(
            out_dir or DEFAULT_OUT_DIR, system, records, tasks,
            seed=seed, repeats=repeats, max_rpm=max_rpm, timestamp=started,
        )
    return records
