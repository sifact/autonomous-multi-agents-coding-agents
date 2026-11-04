# runner

Runs a system over tasks, grades every output with the hidden tests, and saves a reproducible results file.

- `run_benchmark` seeds Python's `random` before each task and repeat (the LLM itself is not seeded), and paces run starts to `max_rpm` if set.
- `final_pass` grades the final files; `first_try_pass` grades `first_files` (the attempt-1 output), reusing the one grade when first and final files are identical.
- A per-task exception becomes a failed record with `error` set and the benchmark continues; three consecutive failures re-raise (e.g. Docker down) after saving.
- `save_results` writes `<out_dir>/<system>-<timestamp>.json` (default `benchmarks/results/`) with model names, settings, seed, repeats, git SHA, task ids, records and aggregate metrics.
- Unpriced models keep `cost_usd` as `null` all the way into the metrics (`mean_cost_usd: null`, `cost_known: false`); it is never rendered as 0.
