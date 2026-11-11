# run.py

Opens one traced run: a named root observation with session and tags, plus the callbacks to hand to LangGraph.

- `trace_run` is a context manager that starts the `coding-agent/<system>` agent observation with the task text as its input, so one run is one trace.
- It also sets LangChain's ambient config, so a model call made without an explicit config (the baselines' ChatGroq call) still reports under the root as a generation.
- `TraceRun.config` is the `{callbacks, metadata}` dict to pass to `run_task`, `run_graph` or `stream_task`; it is empty when tracing is off.
- `set_report` stores a small summary (success, repairs, explanation, tokens, file names) as the trace output, and `score` sends a Langfuse score such as `final_pass`.
- An exception inside the block is recorded as an ERROR on the root and re-raised, and every tracing call is a logged no-op on failure.
