"""A conservative plain-language verdict: did the graph beat the baselines?

Conservative by construction:

- **Paired by task.** Two systems are compared only on the task ids both ran, never on
  percentages over different task sets. Per task the score is the mean over that task's
  repeats, so repeats cannot masquerade as extra tasks.
- **Crashes are not quality.** A task where either side had a crashed run (infrastructure
  failure) is left out and reported. If more than ``MAX_CRASH_SHARE`` of the shared tasks
  must be left out, or a system crashed on every run, the pair is "not comparable".
- **Gate on distinct tasks.** At least ``MIN_SHARED_TASKS`` shared, non-crashed tasks are
  needed; fewer is "no clear difference" (and, honestly, a smoke test: the 10-task fast
  subset can never pass this gate).
- **Two conditions for "better"/"worse".** The mean paired difference must be at least
  ``MIN_POINTS`` percentage points AND an exact two-sided sign test on the non-tied tasks
  must give p < ``ALPHA``. Anything else is "no clear difference".

Every sentence carries the shared-task count, runs per system, wins/losses/ties, the
difference and the token multiple, so a quality gain is never shown without its cost.
"""
from math import comb
from statistics import fmean

from coding_agent.evaluation.metrics import RunRecord
from coding_agent.evaluation.results_io import DEFAULT_VARIANT, ResultFile

MIN_SHARED_TASKS = 20
MIN_POINTS = 5.0
ALPHA = 0.05
MAX_CRASH_SHARE = 0.10
BASELINES = ("single_agent", "single_shot")
CRASH_NOTE = "infrastructure failures, not agent quality"


def sign_test_p(wins: int, losses: int) -> float:
    """Exact two-sided sign test p-value on the non-tied tasks (1.0 when there are none)."""
    n = wins + losses
    if n == 0:
        return 1.0
    tail = sum(comb(n, i) for i in range(min(wins, losses) + 1))
    return min(1.0, 2 * tail / 2**n)


def _judge(diff_pp: float, wins: int, losses: int) -> str:
    """``better`` / ``worse`` / ``unclear``: big enough AND significant AND same direction."""
    if sign_test_p(wins, losses) >= ALPHA:
        return "unclear"
    diff = round(diff_pp, 6)
    if diff >= MIN_POINTS and wins > losses:
        return "better"
    if diff <= -MIN_POINTS and losses > wins:
        return "worse"
    return "unclear"


def _by_task(result: ResultFile) -> dict[str, list[RunRecord]]:
    tasks: dict[str, list[RunRecord]] = {}
    for r in result.records:
        tasks.setdefault(r.task_id, []).append(r)
    return tasks


def _tokens(graph: ResultFile, base: ResultFile) -> str:
    g, b = graph.metrics.mean_tokens, base.metrics.mean_tokens
    if g is None or not b:
        return "token cost not comparable"
    return f"at {g / b:.1f}x the tokens"


def _metric_line(
    name: str, attr: str, ids: list[str], gt: dict, bt: dict, graph: ResultFile,
    base: ResultFile,
) -> tuple[str, str]:
    diffs = [
        fmean(getattr(r, attr) for r in gt[t]) - fmean(getattr(r, attr) for r in bt[t])
        for t in ids
    ]
    wins, losses = sum(d > 0 for d in diffs), sum(d < 0 for d in diffs)
    ties = len(diffs) - wins - losses
    diff_pp = fmean(diffs) * 100
    outcome = _judge(diff_pp, wins, losses)
    verdict = (f"graph is {outcome} than {base.label}" if outcome != "unclear"
               else f"no clear difference between graph and {base.label}")
    runs_g, runs_b = sum(len(gt[t]) for t in ids), sum(len(bt[t]) for t in ids)
    detail = (
        f"{diff_pp:+.1f} pp; {len(ids)} shared tasks, {runs_g} vs {runs_b} runs; "
        f"{wins} wins, {losses} losses, {ties} ties; sign test p={sign_test_p(wins, losses):.3f}"
    )
    return outcome, f"- {name}: {verdict} ({detail}) {_tokens(graph, base)}."


def _compare_one(graph: ResultFile, base: ResultFile) -> list[str]:
    gt, bt = _by_task(graph), _by_task(base)
    prefix = f"- graph vs {base.label}:"
    runs = graph.metrics.n + base.metrics.n
    if graph.metrics.n_errors == graph.metrics.n or base.metrics.n_errors == base.metrics.n:
        crashed = graph.metrics.n_errors + base.metrics.n_errors
        return [f"{prefix} not comparable: {crashed} of {runs} runs crashed ({CRASH_NOTE})."]
    shared = sorted(set(gt) & set(bt))
    sets = ""
    if len(shared) != len(gt) or len(shared) != len(bt):
        sets = (f" graph and {base.label} ran on different task sets "
                f"({len(shared)} shared of {len(gt)} vs {len(bt)});")
    if not shared:
        text = f"{prefix} no clear difference: no shared tasks;{sets} results cannot be paired."
        return [text]
    bad = [t for t in shared if any(r.error for r in gt[t] + bt[t])]
    if len(bad) / len(shared) > MAX_CRASH_SHARE:
        crashed = sum(bool(r.error) for t in shared for r in gt[t] + bt[t])
        shared_runs = sum(len(gt[t]) + len(bt[t]) for t in shared)
        return [f"{prefix} not comparable: {crashed} of {shared_runs} runs crashed ({CRASH_NOTE})."]
    usable = [t for t in shared if t not in bad]
    lines: list[str] = []
    if bad:
        plural = "tasks" if len(bad) != 1 else "task"
        verb = "were" if len(bad) != 1 else "was"
        lines.append(f"- {len(bad)} {plural} with crashed runs {verb} excluded from the "
                     f"comparison with {base.label}.")
    if len(usable) < MIN_SHARED_TASKS:
        text = (f"{prefix} no clear difference: only {len(usable)} shared tasks (need at least "
                f"{MIN_SHARED_TASKS});{sets} results on so few tasks are a smoke test only.")
        return [text, *lines]
    final, text = _metric_line(
        "Final pass", "final_pass", usable, gt, bt, graph, base)
    matched, text2 = _metric_line(
        "Budget-matched pass", "matched_budget_pass", usable, gt, bt, graph, base)
    lines = [text, text2, *lines]
    if final == "better" and matched != "better":
        lines.append(
            f"- The gain disappears when the retry budget is matched, so the final-pass gain "
            f"over {base.label} may come from extra retries rather than better agents."
        )
    elif final != matched:
        lines.append(
            f"- Final pass and budget-matched pass disagree against {base.label}; treat this "
            "as no clear result."
        )
    return lines


def compare(results: list[ResultFile]) -> str:
    """Say, from the numbers only, how the full graph did against each baseline."""
    head = "Verdict (paired by task, from the numbers above only):"
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
        if name in latest:
            lines += _compare_one(graph, latest[name])
    if len(lines) == 1:
        lines.append("- No baseline result (single_agent or single_shot) to compare against.")
    return "\n".join(lines)
