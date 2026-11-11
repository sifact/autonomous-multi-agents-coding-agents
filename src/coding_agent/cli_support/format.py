"""Small text formatters shared by the CLI commands."""
from __future__ import annotations

from coding_agent.evaluation import Metrics, RunRecord

TAIL_LINES = 6
TAIL_CHARS = 600


def money(cost: float | None) -> str:
    """Cost for display; unknown is "n/a", never a made-up zero."""
    return "n/a" if cost is None else f"${cost:.4f}"


def tail(text: str, lines: int = TAIL_LINES, chars: int = TAIL_CHARS) -> str:
    """Last few lines of program output, clipped, for a one-glance view."""
    kept = [ln for ln in text.strip().splitlines() if ln.strip()][-lines:]
    out = "\n".join(kept)
    return out[-chars:]


def pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.0%}"


def num(value: float | None, digits: int = 1) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def record_line(r: RunRecord) -> str:
    status = "ERROR" if r.error else ("PASS" if r.final_pass else "FAIL")
    line = (
        f"{r.task_id:<28} {status:<5} attempts={r.attempts} "
        f"tokens={r.tokens_in + r.tokens_out} {r.wall_s:.1f}s"
    )
    return f"{line}  ({r.error})" if r.error else line


def metrics_lines(m: Metrics) -> list[str]:
    cost = m.mean_cost_usd if m.cost_known else None
    return [
        f"runs:                     {m.n_records}",
        f"pass@1:                   {pct(m.pass_at_1)}",
        f"final pass:               {pct(m.final_pass_rate)}",
        f"matched-budget pass:      {pct(m.matched_budget_pass_rate)}",
        f"runtime errors fixed<=3:  {pct(m.runtime_errors_fixed_pct)}",
        f"mean attempts:            {num(m.mean_attempts)}",
        f"mean tokens:              {num(m.mean_tokens, 0)}",
        f"mean cost per run:        {money(cost)}",
        f"mean wall time:           {num(m.mean_wall_s)}s",
        f"crashed runs (n_errors):  {m.n_errors}",
    ]
