"""Hand-written result files for the report tests (no model, no Docker)."""
import json
from pathlib import Path

SETTINGS = {"max_repairs": 3, "max_replans": 2, "step_budget": 40}


def rec(task_id, system, *, first=False, final=False, matched=None, err=None, cost=0.01,
        attempts=1, tin=600, tout=400, wall=2.0, runtime_error=False, fixed=False, repeat=0):
    return {
        "task_id": task_id, "system": system, "first_try_pass": first, "final_pass": final,
        "matched_budget_pass": final if matched is None else matched,
        "had_runtime_error": runtime_error, "fixed_within_3": fixed, "attempts": attempts,
        "tokens_in": tin, "tokens_out": tout, "cost_usd": cost, "wall_s": wall, "error": err,
        "repeat": repeat, "fixed_and_passed": fixed and final,
    }


def payload(system, records, *, variant=None, ts="2026-11-06T10:00:00+00:00", sha="abcdef1234567",
            dirty=False, models=None):
    data = {
        "system": system, "models": models or {"cheap": "m-small", "strong": "m-big"},
        "resolved_roles": {}, "settings": SETTINGS, "budget_note": "BUDGET NOTE TEXT",
        "seed": 0, "repeats": 1, "git_sha": sha, "git_dirty": dirty, "timestamp": ts,
        "task_ids": sorted({r["task_id"] for r in records}), "records": records,
        "metrics": None,
    }
    if variant is not None:
        data["variant"] = variant
    return data


def write(directory: Path, name: str, data) -> Path:
    path = directory / name
    path.write_text(data if isinstance(data, str) else json.dumps(data))
    return path


def runs(system, n, passes, **kw):
    """n records on tasks t0..t(n-1); the first ``passes`` pass."""
    return [rec(f"t{i}", system, final=i < passes, first=i < passes, **kw) for i in range(n)]
