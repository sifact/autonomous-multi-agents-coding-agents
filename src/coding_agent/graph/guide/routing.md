# routing.py

Pure functions that decide where the graph goes after review and why a run ended.

- `route_after_review` returns "coder", "planner" or "end" from the verdict and the counters in state.
- `pass`, `stop`, a missing verdict or an unknown action all route to "end".
- `fix` goes to the coder while `repairs < max_repairs`; `replan` goes to the planner while `replans < max_replans`.
- `visits >= step_budget` forces "end" regardless of the verdict.
- `stop_reason` gives a readable cause for every failed end (caps, budget, stop, no verdict) and None on success.
