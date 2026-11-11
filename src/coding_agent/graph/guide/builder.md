# builder.py

Wires the five agent nodes and a finalize step into a LangGraph state machine, and runs it.

- `build_graph(router, sandbox, settings, skip_planner=, skip_architect=)` fetches one model and its resolved name per role (planner, architect, coder, debugger, reviewer) and injects them, the sandbox and the settings into the node factories.
- The ablation switches replace the planner or architect node with a zero-cost pass-through (event `skipped: True`, no model fetched or called) that keeps the edges, visit counts and replan counters; the architect's empty layout means "the coder decides".
- Edges run START → planner → architect → coder → executor → reviewer, then a conditional edge on `route_after_review` maps "coder" to a repair, "planner" to a replan and "end" to `finalize`.
- `finalize` is a real node that stores `build_report`'s FinalReport in `final`, so streaming callers get the result as the last update; the compiled graph carries `recursion_limit = step_budget + 10` as a second backstop behind the router's step budget.
- `stream_task` yields `(node, update)` pairs live for the CLI and web UI; `run_graph` returns the final state and `run_task` returns only the FinalReport; all three take an optional `config` (callbacks, metadata) that tracing uses.
