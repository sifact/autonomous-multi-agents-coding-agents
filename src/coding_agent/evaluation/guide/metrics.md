# metrics.py

Turns per-run records into the headline evaluation numbers.

- `RunRecord` is one system's outcome on one task: pass flags, attempts, tokens, cost, wall time.
- `aggregate` computes pass@1 and final pass rate as plain means of the boolean flags.
- `runtime_errors_fixed_pct` is fixed-within-3 over runs that had a runtime error, or `None` if none did.
- Mean tokens counts input plus output tokens; cost, attempts and wall time are plain means.
- An empty record list raises `ValueError` rather than returning misleading zeros.
