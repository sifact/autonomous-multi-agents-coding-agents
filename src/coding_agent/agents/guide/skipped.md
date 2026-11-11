# skipped.py

Zero-cost stand-ins for the planner and architect, used by the ablation variants.

- `make_skipped_planner()` makes no model call and returns a one-step plan holding the task text plus the single criterion "the program runs and does what the task asks".
- `make_skipped_architect()` returns an empty layout, which the coder prompt reads as "choose the files yourself".
- Both bump `visits` so the step budget stays a real backstop, and both emit an event with `skipped: True` and zero tokens so usage counts only the roles that ran.
- The skipped planner still applies the replan counters (replans+1, repairs reset, verdict cleared), so a reviewer that always says `replan` ends after `max_replans` instead of looping.
- Run results label the variants `graph (no planner)` and `graph (no architect)`, so the table shows what each role contributes.
