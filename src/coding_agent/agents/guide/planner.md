# planner.py

Builds the planner node, which turns the task (or a failed plan) into steps and acceptance criteria.

- `make_planner(model)` returns a node that asks the "planner" model for JSON `{"steps": [...], "criteria": [...]}` and validates it with the `Plan` schema.
- When the last verdict was `replan` it shows the previous plan, the reviewer's reason and the stderr tail, then calls `apply_verdict_counters` (replans+1, repairs reset to 0, verdict cleared).
- The verdict is read before the update is built, because `apply_verdict_counters` clears it.
- Malformed JSON is retried once (`invoke_json`); after two failures it falls back to one step restating the task, and records the parse error in its event.
- Every update includes `bump_visit` and one `planner` event with token counts, step count and whether it was a replan.
