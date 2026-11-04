"""Per-run records and their aggregate headline metrics.

Crashed runs (``error`` set) count as FAILURES in every pass rate but are left
out of the resource means (attempts, tokens, cost, wall time): a crash that
stopped early must not make a system look cheaper or faster. Their spend is
still visible in ``total_tokens_all``.
"""
from dataclasses import dataclass
from statistics import fmean


@dataclass(frozen=True)
class RunRecord:
    """Outcome of one system run on one task."""

    task_id: str
    system: str
    first_try_pass: bool
    final_pass: bool
    # Hidden-test result of the generation at the shared retry budget (see
    # SystemOutput.budget_files): comparable across systems with different retry rules.
    matched_budget_pass: bool
    had_runtime_error: bool
    fixed_within_3: bool
    attempts: int
    tokens_in: int
    tokens_out: int
    cost_usd: float | None  # None when the model has no known price (never 0)
    wall_s: float
    error: str | None = None  # set when the run crashed; the record then counts as failed
    repeat: int = 0
    fixed_and_passed: bool = False  # fixed_within_3 AND final_pass


@dataclass(frozen=True)
class Metrics:
    """Headline numbers over a set of runs. Fractions are in [0, 1]."""

    n: int  # all records (same as n_records)
    n_records: int
    n_errors: int  # crashed runs: failures in pass rates, excluded from resource means
    pass_at_1: float
    final_pass_rate: float
    matched_budget_pass_rate: float
    runtime_errors_fixed_pct: float | None  # None when no run hit a runtime error
    fixed_and_passed_pct: float | None  # of runs with a runtime error, share fixed AND passing
    mean_attempts: float | None  # resource means: error-free records only; None if there are none
    mean_cost_usd: float | None  # ...and only those with a known cost
    cost_known_count: int
    cost_known: bool  # True only when every error-free run's cost was known
    mean_tokens: float | None
    mean_wall_s: float | None
    total_tokens_all: int  # tokens of ALL records, crashes included


def aggregate(records: list[RunRecord]) -> Metrics:
    """Summarise runs; raises ValueError on an empty list (no honest mean exists)."""
    if not records:
        raise ValueError("cannot aggregate zero records")
    ok = [r for r in records if r.error is None]
    errored = [r for r in records if r.had_runtime_error]
    costs = [r.cost_usd for r in ok if r.cost_usd is not None]

    def mean(values) -> float | None:
        values = list(values)
        return fmean(values) if values else None

    return Metrics(
        n=len(records),
        n_records=len(records),
        n_errors=len(records) - len(ok),
        pass_at_1=fmean(r.first_try_pass for r in records),
        final_pass_rate=fmean(r.final_pass for r in records),
        matched_budget_pass_rate=fmean(r.matched_budget_pass for r in records),
        runtime_errors_fixed_pct=(
            sum(r.fixed_within_3 for r in errored) / len(errored) if errored else None
        ),
        fixed_and_passed_pct=(
            sum(r.fixed_and_passed for r in errored) / len(errored) if errored else None
        ),
        mean_attempts=mean(r.attempts for r in ok),
        mean_cost_usd=mean(costs),
        cost_known_count=len(costs),
        cost_known=bool(ok) and len(costs) == len(ok),
        mean_tokens=mean(r.tokens_in + r.tokens_out for r in ok),
        mean_wall_s=mean(r.wall_s for r in ok),
        total_tokens_all=sum(r.tokens_in + r.tokens_out for r in records),
    )
