# builder.py

Wires the five agent nodes and a finalize step into a LangGraph state machine, and runs it.

- `build_graph(router, sandbox, settings)` fetches one model and its resolved name per role (planner, architect, coder, debugger, reviewer) and injects them, the sandbox and the settings into the node factories.
- Edges run START → planner → architect → coder → executor → reviewer, then a conditional edge on `route_after_review` maps "coder" to a repair, "planner" to a replan and "end" to `finalize`.
- `finalize` is a real node that stores `build_report`'s FinalReport in `final`, so streaming callers get the result as the last update.
- The compiled graph carries `recursion_limit = step_budget + 10`; the router's step budget ends runs first, so this is only a second backstop.
- `stream_task` yields `(node, update)` pairs live for the CLI and web UI; `run_graph` returns the final state and `run_task` returns only the FinalReport; all three take an optional `config` (callbacks, metadata) that tracing uses.
