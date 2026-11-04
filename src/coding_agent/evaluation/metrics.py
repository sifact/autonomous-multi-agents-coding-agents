"""Per-run records and their aggregate headline metrics."""
from dataclasses import dataclass
from statistics import fmean


@dataclass(frozen=True)
class RunRecord:
    """Outcome of one system run on one task."""

    task_id: str
    system: str
    first_try_pass: bool
    final_pass: bool
    had_runtime_error: bool
    fixed_within_3: bool
    attempts: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    wall_s: float


@dataclass(frozen=True)
class Metrics:
    """Headline numbers over a set of runs. Fractions are in [0, 1]."""

    n: int
    pass_at_1: float
    final_pass_rate: float
    runtime_errors_fixed_pct: float | None  # fraction in [0, 1]; None when no run hit a runtime error
    mean_attempts: float
    mean_cost_usd: float
    mean_tokens: float
    mean_wall_s: float


def aggregate(records: list[RunRecord]) -> Metrics:
    """Summarise runs; raises ValueError on an empty list (no honest mean exists)."""
    if not records:
        raise ValueError("cannot aggregate zero records")
    errored = [r for r in records if r.had_runtime_error]
    fixed_pct = sum(r.fixed_within_3 for r in errored) / len(errored) if errored else None
    return Metrics(
        n=len(records),
        pass_at_1=fmean(r.first_try_pass for r in records),
        final_pass_rate=fmean(r.final_pass for r in records),
        runtime_errors_fixed_pct=fixed_pct,
        mean_attempts=fmean(r.attempts for r in records),
        mean_cost_usd=fmean(r.cost_usd for r in records),
        mean_tokens=fmean(r.tokens_in + r.tokens_out for r in records),
        mean_wall_s=fmean(r.wall_s for r in records),
    )
