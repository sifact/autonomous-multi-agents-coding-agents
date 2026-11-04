# routing.py

Pure functions that decide where the graph goes after review and why a run ended.

- `route_after_review` returns "coder", "planner" or "end" from the verdict and the counters in state.
- `repairs`/`replans` mean work already performed; the router reads them before any bump, and the coder or planner (never the reviewer) applies the bump.
- `fix` goes to the coder while `repairs < max_repairs`; `replan` goes to the planner while `replans < max_replans`; pass, stop, a missing verdict or an unknown action end the run.
- `visits >= step_budget` forces "end" regardless of the verdict; every node must bump `visits`.
- `stop_reason` gives a readable cause for every failed end and None on success; call it only after the router returned "end".
