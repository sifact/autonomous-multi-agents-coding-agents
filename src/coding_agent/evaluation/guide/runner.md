# runner.py

Runs a system over tasks, grades every output with the hidden tests, and saves a reproducible results file.

- `run_benchmark` seeds Python's `random` with `seed + repeat` before each run (the LLM itself is not seeded) and spaces run starts to `max_runs_per_min` if set.
- It grades three file sets with the hidden tests, reusing a grade when file sets are identical: final (`final_pass`), attempt 1 (`first_try_pass`) and generation `max_repairs + 1` (`matched_budget_pass`, the budget-matched figure).
- A per-task exception becomes a failed record that keeps the partial tokens and wall time the system attached; three consecutive failures of any exception type re-raise, and results are saved in a `finally`, so partial results survive a crash or Ctrl-C.
- `save_results` writes `<out_dir>/<system>-<timestamp with microseconds>.json` (default `benchmarks/results/` under the repo root, not the CWD) with model names, resolved roles, settings and budgets, a plain-language `budget_note`, seed, repeats, git SHA and `git_dirty`, task ids, records and metrics.
- Unpriced models keep `cost_usd` as `null` through to the metrics (`mean_cost_usd: null`, `cost_known: false`); it is never rendered as 0.
