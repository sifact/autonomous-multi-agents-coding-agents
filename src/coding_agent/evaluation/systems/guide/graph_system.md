# graph_system.py

The multi-agent graph as an eval system.

- Builds a fresh `UsageTracker` and `ModelRouter` (via `router_factory(tracker)`) for every task, so tokens and cost are per-run and comparable.
- Passes the task text plus `task.fixtures` into `run_graph`, so every node sees the fixture previews and the executor writes the files.
- Derives attempts (coder events), runtime errors and `fixed` from the graph's code versions, and `first_files` from version 1.
- `budget_files` is `versions[min(len - 1, max_repairs)]`, the 4th generation, so replans that reset repairs do not inflate the matched-budget result.
- On a crash it attaches the tracker's usage to the exception; `describe()` reports cheap/strong models plus the roles the router actually resolved.
