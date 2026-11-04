# router.py

Chooses which model serves each agent role and records token and cost usage.

- Planner, architect and reviewer use the cheap model; coder and debugger use the strong one.
- `all_strong=True` sends every role to the strong model for the ablation study.
- `overrides={"planner": "model"}` pins a single role, independent of Settings.
- With a `UsageTracker`, every returned model is wrapped so each call is logged under its model name.
- `UsageTracker` is thread-safe, keeps per-model totals, and exposes `cost_known` when any price is missing.
