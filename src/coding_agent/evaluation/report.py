"""Render the ablation table: one row per system or graph variant, plus how to read it.

Everything printed comes from the result files, never from this module, and the
output has no timestamps of its own, so writing it into the README twice gives
the same text. Unknown values print as ``n/a``, never as 0.
"""
from pathlib import Path

from coding_agent.evaluation.breakdown import render_breakdown
from coding_agent.evaluation.results_io import (
    ResultFile,
    ResultFileWarning,
    load_results,
    select_latest,
)
from coding_agent.evaluation.systems import SKIPPED, SKIPPED_ROLE
from coding_agent.evaluation.verdict import compare

__all__ = ["ResultFileWarning", "compare", "load_results", "render_markdown"]

COLUMNS = (
    "System", "Tasks", "Runs", "pass@1", "Final pass*", "Budget-matched pass",
    "Runtime errors fixed (<=3 repairs)", "Mean attempts", "Mean tokens",
    "Mean cost (per task)", "Mean wall time", "Errors",
)
TABLE_FOOTNOTE = (
    "\\* retry-confounded: the graph can try more times than the loop; "
    "compare Budget-matched pass"
)
READING_GUIDE = """\
**How to read this table**

- **pass@1**: share of runs whose first generated program passes the hidden tests.
- **Final pass***: share that pass after the system's own repairs or replans. The graph can \
retry more often than the single agent, so this number is confounded by retry budget.
- **Budget-matched pass**: grades the generation at the shared retry budget; this is the fair \
comparison.
- **Runtime errors fixed**: of the runs where the program crashed at least once, the share that \
ended working within 3 repairs; `n/a` when no run crashed.
- **Means** (attempts, tokens, cost, wall time) cover error-free runs only; **Errors** counts \
runs that crashed (infrastructure failures), which count as failures in the pass rates. `n/a` \
means unknown, never zero; "k of n priced" means only some runs had a known model price, so the \
cost is a partial mean."""


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def _num(value: float | None, digits: int = 1, suffix: str = "") -> str:
    return "n/a" if value is None else f"{value:,.{digits}f}{suffix}"


def _cost(result: ResultFile) -> str:
    m = result.metrics
    if m.mean_cost_usd is None:
        return "n/a"
    text = f"${m.mean_cost_usd:.4f}"
    ok = m.n_records - m.n_errors
    return text if m.cost_known else f"{text} ({m.cost_known_count} of {ok} priced)"


def row_label(result: ResultFile, all_runs: bool) -> str:
    if not all_runs:
        return result.label
    parts = [result.label, result.timestamp.strftime("%Y-%m-%d %H:%M UTC")]
    parts.append((result.git_sha or "no sha")[:7])
    if result.git_dirty:
        parts.append("dirty")
    return " · ".join(parts)


def _row(result: ResultFile, all_runs: bool) -> str:
    m = result.metrics
    cells = [
        row_label(result, all_runs), str(len({r.task_id for r in result.records})), str(m.n),
        _pct(m.pass_at_1), _pct(m.final_pass_rate), _pct(m.matched_budget_pass_rate),
        _pct(m.runtime_errors_fixed_pct), _num(m.mean_attempts), _num(m.mean_tokens, 0),
        _cost(result), _num(m.mean_wall_s, 1, "s"), str(m.n_errors),
    ]
    return "| " + " | ".join(cells) + " |"


def _detail(result: ResultFile, all_runs: bool) -> str:
    models = dict(result.resolved_roles or result.models)
    if result.variant in SKIPPED_ROLE:  # never show a model name for a role that did not run
        models[SKIPPED_ROLE[result.variant]] = SKIPPED
    model_text = ", ".join(f"{k}={v}" for k, v in models.items()) or "unknown"
    s = result.settings
    budgets = ", ".join(
        f"{label} {s[key]}" for key, label in
        (("max_repairs", "max repairs"), ("max_replans", "max replans"),
         ("step_budget", "step budget")) if key in s
    ) or "not recorded"
    seed = f"seed {result.seed}, repeats {result.repeats}"
    return f"- {row_label(result, all_runs)}: models {model_text}; {seed}; budgets: {budgets}."


def render_markdown(
    results: list[ResultFile], *, by_category: bool = False, all_runs: bool = False,
    tasks_dir: Path | None = None,
) -> str:
    """The results report. Latest file per system/variant, or every file with ``all_runs``."""
    latest = select_latest(results)
    rows = sorted(results, key=lambda r: r.sort_key) if all_runs else latest
    out = ["### Ablation results", "", "| " + " | ".join(COLUMNS) + " |",
           "|" + "---|" * len(COLUMNS)]
    out += [_row(r, all_runs) for r in rows]
    out += ["", TABLE_FOOTNOTE, "", READING_GUIDE, "", "**Run details**", ""]
    out += [_detail(r, all_runs) for r in rows]
    notes = list(dict.fromkeys(r.budget_note for r in rows if r.budget_note))
    for note in notes:
        out += ["", f"> Budget note: {note}"]
    if by_category:
        labels = [row_label(r, all_runs) for r in rows]
        out += ["", render_breakdown(rows, labels, tasks_dir)]
    out += ["", "### Verdict", "", compare(latest)]
    return "\n".join(out) + "\n"
