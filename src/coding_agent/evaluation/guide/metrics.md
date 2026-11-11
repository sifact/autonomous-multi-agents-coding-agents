# metrics.py

Turns per-run records into the headline evaluation numbers.

- `RunRecord` is one run: pass flags (`first_try_pass`, `final_pass`, `matched_budget_pass`), `fixed_and_passed`, attempts, tokens, cost (`float | None`), wall time, `repeat` and `error`.
- `final_pass_rate` is confounded with retry budget (the graph can replan and make more generations than the loop); `matched_budget_pass_rate` grades the generation at the shared budget and is the fair comparison.
- Crashed runs (`error` set) count as failures in every pass rate but are excluded from `mean_attempts`, `mean_tokens`, `mean_cost_usd` and `mean_wall_s`; `n_errors`, `n_records` and `total_tokens_all` keep their spend visible; a run with an unknown (None) token count is left out of the token numbers, never counted as zero.
- `runtime_errors_fixed_pct` and `fixed_and_passed_pct` are taken over runs that hit a runtime error (`None` if none did); the second also requires the hidden tests to pass.
- Cost is `None` for unpriced models, never 0: `mean_cost_usd` averages only known costs, and `cost_known_count` / `cost_known` tell reports when to show "n/a".
