# state.py

Defines the shared graph state and the value types passed between agents.

- `AgentState` is a TypedDict; only `events` has a reducer (`operator.add`), every other key overwrites.
- `Step`, `Verdict` and `FinalReport` are pydantic models; `Verdict` lower-cases and strips `action`, defaults `reason` to empty and clips it to 500 characters instead of failing.
- `initial_state(task)` returns zeroed counters and fresh, unshared containers.
- `bump_visit` is included in every node's update (planner, architect, coder, executor, reviewer, finalize), so the 40-visit budget (worst case about 39) is a real backstop.
- `apply_verdict_counters` is called by the coder on `fix` or the planner on `replan`, never by the reviewer (its update lands before the router reads state); it also clears `verdict` so one verdict is never counted twice.
