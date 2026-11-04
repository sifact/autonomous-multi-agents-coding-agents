# router.py

Chooses which model serves each agent role and records token and cost usage.

- Planner, architect and reviewer use the cheap model; coder and debugger use the strong one.
- `all_strong=True` sends every role to the strong model; `overrides={"planner": "model"}` pins one role.
- One model instance is cached per model name, and `Settings.max_rpm` builds a single `RateLimiter` shared by all of them.
- With a `UsageTracker`, every returned model is wrapped so each call is logged under its model name.
- `UsageTracker` is thread-safe with per-model totals; `total_cost` is `None` when any used model has no known price (`cost_known` is False).
