"""A conservative plain-language verdict: did the graph beat the baselines?

Why conservative: a benchmark of a few dozen tasks cannot separate small
differences from luck. A difference is only called when BOTH systems have at
least ``MIN_RUNS`` runs and the gap is at least ``MIN_POINTS`` percentage points
AND ``MIN_TASKS`` runs' worth. Everything else reads "no clear difference". The
sentence always carries the sample sizes. It is not a significance test.
"""
from coding_agent.evaluation.results_io import DEFAULT_VARIANT, ResultFile

MIN_RUNS = 20
MIN_POINTS = 5.0
MIN_TASKS = 2
BASELINES = ("single_agent", "single_shot")


def _judge(g: float, b: float, n_g: int, n_b: int) -> tuple[str, str]:
    """``(outcome, detail)`` with outcome in better / worse / unclear / too_few."""
    points = round((g - b) * 100, 6)
    shown = f"{g:.1%} vs {b:.1%}"
    if min(n_g, n_b) < MIN_RUNS:
        return "too_few", (
            f"{shown}; only {n_g} vs {n_b} runs, at least {MIN_RUNS} per system are needed"
        )
    tasks_apart = round(abs(g - b) * min(n_g, n_b), 6)
    if abs(points) < MIN_POINTS or tasks_apart < MIN_TASKS:
        return "unclear", (
            f"{shown}, {points:+.1f} points; {n_g} vs {n_b} runs; a difference needs at least "
            f"{MIN_POINTS:g} points and {MIN_TASKS} tasks"
        )
    return ("better" if points > 0 else "worse"), (
        f"{shown}, {points:+.1f} points; {n_g} vs {n_b} runs"
    )


def _metric_line(name: str, g: float, b: float, n_g: int, n_b: int, base: str) -> tuple[str, str]:
    outcome, detail = _judge(g, b, n_g, n_b)
    if outcome in ("better", "worse"):
        return outcome, f"- {name}: graph is {outcome} than {base} ({detail})."
    return outcome, f"- {name}: no clear difference between graph and {base} ({detail})."


def _cost_line(graph: ResultFile, base: ResultFile) -> str:
    g, b = graph.metrics.mean_tokens, base.metrics.mean_tokens
    if g is None or not b:
        return f"- Cost: tokens cannot be compared with {base.label} (no error-free runs)."
    return (f"- Cost: graph used about {g / b:.1f}x the tokens of {base.label} per task "
            f"(mean {g:,.0f} vs {b:,.0f}).")


def compare(results: list[ResultFile]) -> str:
    """Say, from the numbers only, how the full graph did against each baseline."""
    head = "Verdict (from the numbers above only; this is not a significance test):"
    if not results:
        return f"{head}\n- No results to compare."
    latest: dict[str, ResultFile] = {}
    for r in results:
        if r.variant == DEFAULT_VARIANT and (
                r.system not in latest or r.timestamp > latest[r.system].timestamp):
            latest[r.system] = r
    graph = latest.get("graph")
    if graph is None:
        return f"{head}\n- No graph result (full variant) to compare."
    lines = [head]
    for name in BASELINES:
        base = latest.get(name)
        if base is None:
            continue
        gm, bm = graph.metrics, base.metrics
        final, text = _metric_line(
            "Final pass", gm.final_pass_rate, bm.final_pass_rate, gm.n, bm.n, name)
        lines.append(text)
        matched, text = _metric_line(
            "Budget-matched pass", gm.matched_budget_pass_rate, bm.matched_budget_pass_rate,
            gm.n, bm.n, name)
        lines.append(text)
        lines.append(_cost_line(graph, base))
        if final == "better" and matched != "better":
            lines.append(
                f"- The graph's final-pass gain over {name} is not there at a matched retry "
                "budget, so it may come from extra retries rather than better agents."
            )
    if len(lines) == 1:
        lines.append("- No baseline result (single_agent or single_shot) to compare against.")
    return "\n".join(lines)
