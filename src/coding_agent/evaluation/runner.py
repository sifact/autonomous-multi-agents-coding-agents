"""Benchmark runner: solve each task, grade with the HIDDEN tests, record, save.

Reproducibility: Python's ``random`` is seeded with ``seed + repeat`` before every
run. The LLM itself is NOT seeded (providers do not guarantee determinism), so
repeats will differ; use ``repeats`` to see the spread.

Grading: ``final_pass`` grades the system's final files; ``first_try_pass`` grades
``SystemOutput.first_files`` (attempt 1); ``matched_budget_pass`` grades
``SystemOutput.budget_files`` (generation ``max_repairs + 1``, so systems with
different retry rules are compared at the same budget). Identical file sets are
graded once and the grade is reused.

Failures: an exception in one task becomes a failed record (``error`` set, with the
tokens and wall time the system had already spent when it attached them to the
exception) and the benchmark continues. After 3 consecutive such failures of any
exception type the last one is re-raised (infrastructure such as Docker being
down would otherwise silently produce a file full of zeros). Results are saved
in a ``finally``, so partial results survive a crash or Ctrl-C.
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
from coding_agent.llm import Usage
from coding_agent.sandbox import Sandbox

REPO_ROOT = Path(__file__).resolve().parents[3]  # src/coding_agent/evaluation -> repo root
DEFAULT_OUT_DIR = REPO_ROOT / "benchmarks" / "results"
BUDGET_NOTE = (
    "Systems have different retry budgets: the graph can replan, which resets its repair "
    "count, so it may make more code generations than the single-agent loop (max_repairs + 1). "
    "final_pass_rate is therefore confounded with retry budget; matched_budget_pass_rate grades "
    "the generation at the shared retry budget (generation max_repairs + 1, or the last one if "
    "fewer were made) and is the fair comparison. Budgets used are in settings."
)
MAX_CONSECUTIVE_FAILURES = 3
_sleep = time.sleep  # patched in tests


def _git(*args: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", *args], capture_output=True, text=True, timeout=10, check=False,
            cwd=REPO_ROOT,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout if proc.returncode == 0 else None


def git_sha() -> str | None:
    """HEAD commit of the repo, or None when git or the repo is unavailable."""
    out = _git("rev-parse", "HEAD")
    return out.strip() or None if out is not None else None


def git_dirty() -> bool | None:
    """True when the working tree has uncommitted changes; None when unknown."""
    out = _git("status", "--porcelain")
    return None if out is None else bool(out.strip())


def _grade_record(
    task: Task, system_name: str, out: SystemOutput, sandbox: Sandbox, repeat: int
) -> RunRecord:
    graded: list[tuple[dict[str, str], bool]] = []

    def passed(files: dict[str, str]) -> bool:
        for seen, result in graded:
            if seen == files:
                return result
        result = grade(task, files, sandbox).passed
        graded.append((files, result))
        return result

    final = passed(out.files)
    first = final if out.first_files is None else passed(out.first_files)
    matched = final if out.budget_files is None else passed(out.budget_files)
    return RunRecord(
        task_id=task.id, system=system_name, first_try_pass=first, final_pass=final,
        matched_budget_pass=matched, had_runtime_error=out.had_runtime_error,
        fixed_within_3=out.fixed, attempts=out.attempts, tokens_in=out.usage.tokens_in,
        tokens_out=out.usage.tokens_out, cost_usd=out.cost_usd, wall_s=out.wall_s,
        error=out.error, repeat=repeat, fixed_and_passed=out.fixed and final,
    )


def _crash_record(
    task: Task, system_name: str, exc: Exception, elapsed_s: float, repeat: int
) -> RunRecord:
    """Failed record that keeps whatever the system had spent (attached by ``attach_partial``)."""
    usage = getattr(exc, "partial_usage", Usage(0, 0))
    return RunRecord(
        task_id=task.id, system=system_name, first_try_pass=False, final_pass=False,
        matched_budget_pass=False, had_runtime_error=False, fixed_within_3=False, attempts=0,
        tokens_in=usage.tokens_in, tokens_out=usage.tokens_out,
        cost_usd=getattr(exc, "partial_cost_usd", None),
        wall_s=getattr(exc, "partial_wall_s", elapsed_s),
        error=f"{type(exc).__name__}: {exc}", repeat=repeat,
    )


def save_results(
    out_dir: Path, system: System, records: list[RunRecord], tasks: list[Task], *,
    seed: int, repeats: int, max_runs_per_min: int | None, timestamp: datetime,
) -> Path:
    """Write ``<out_dir>/<system>-<timestamp>.json`` and return its path (None -> null)."""
    info = system.describe()
    payload: dict[str, Any] = {
        "system": system.name,
        "models": info.get("models", {}),
        "resolved_roles": info.get("resolved_roles", {}),
        "settings": info.get("settings", {}),
        "budget_note": BUDGET_NOTE,
        "seed": seed,
        "repeats": repeats,
        "max_runs_per_min": max_runs_per_min,
        "git_sha": git_sha(),
        "git_dirty": git_dirty(),
        "timestamp": timestamp.isoformat(),
        "task_ids": [t.id for t in tasks],
        "records": [dataclasses.asdict(r) for r in records],
        "metrics": dataclasses.asdict(aggregate(records)) if records else None,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{system.name}-{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}.json"
    path.write_text(json.dumps(payload, indent=2))
    return path


def run_benchmark(
    tasks: list[Task], system: System, sandbox: Sandbox, repeats: int = 1, seed: int = 0,
    max_runs_per_min: int | None = None, out_dir: Path | None = None,
    on_record: Callable[[RunRecord], None] | None = None,
) -> list[RunRecord]:
    """Run ``system`` over ``tasks`` x ``repeats``, grade with hidden tests, save, return records.

    ``max_runs_per_min`` is coarse pacing: run starts are spaced at least
    ``60 / max_runs_per_min`` seconds apart. The per-request limiter
    (``Settings.max_rpm``) lives in the Groq client; this only keeps a benchmark
    of many quick tasks from bursting.
    """
    started = datetime.now(UTC)
    records: list[RunRecord] = []
    failures = 0
    last_exc: Exception | None = None
    last_start: float | None = None
    try:
        for repeat in range(repeats):
            for task in tasks:
                if max_runs_per_min and last_start is not None:
                    wait = 60 / max_runs_per_min - (time.monotonic() - last_start)
                    if wait > 0:
                        _sleep(wait)
                last_start = time.monotonic()
                random.seed(seed + repeat)
                try:
                    record = _grade_record(task, system.name, system.solve(task), sandbox, repeat)
                    failures = 0
                except Exception as exc:  # noqa: BLE001 - one task must not kill the benchmark
                    record = _crash_record(
                        task, system.name, exc, time.monotonic() - last_start, repeat)
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
            seed=seed, repeats=repeats, max_runs_per_min=max_runs_per_min, timestamp=started,
        )
    return records
