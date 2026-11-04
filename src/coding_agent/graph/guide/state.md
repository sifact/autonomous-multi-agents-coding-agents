# state.py

Defines the shared graph state and the value types passed between agents.

- `AgentState` is a TypedDict; only `events` has a reducer (`operator.add`), every other key overwrites.
- `Step`, `Verdict` and `FinalReport` are pydantic models so model JSON can be parsed straight into them.
- `Verdict.reason` is clipped to 500 characters rather than rejected, so a valid action is never lost to a rambling reason.
- `initial_state(task)` returns zeroed counters and fresh, unshared containers.
- `apply_verdict_counters` returns the partial update: fix bumps repairs, replan bumps replans and resets repairs, pass/stop change nothing.
