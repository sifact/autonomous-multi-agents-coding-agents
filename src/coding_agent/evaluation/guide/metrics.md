# metrics.py

Turns per-run records into the headline evaluation numbers.

- `RunRecord` is one system's outcome on one task: pass flags, attempts, tokens, cost (`float | None`), wall time.
- `aggregate` computes pass@1 and final pass rate as plain means of the boolean flags; an empty list raises `ValueError`.
- `runtime_errors_fixed_pct` is fixed-within-3 over runs that had a runtime error, or `None` if none did.
- Mean tokens counts input plus output tokens; attempts and wall time are plain means.
- Cost is `None` for unpriced models, never 0: `mean_cost_usd` averages only known costs, and `cost_known_count` / `cost_known` tell reports when to show "n/a".
