# metadata.py

Builds the LangChain-config metadata that Langfuse turns into trace attributes.

- `trace_metadata(run_id, system, task_id, tags=...)` returns a plain dict to put in the run config.
- `langfuse_session_id` is the run id; for evaluation it is the result file id, so all task runs of one benchmark group into one session.
- `langfuse_trace_name` is `coding-agent/<system>`, which keeps traces findable by system.
- `langfuse_tags` lists the system name, the task id and any extra tags (such as the task category), without duplicates and in order.
- Only `langfuse_*` keys are produced, so nothing else leaks into trace metadata.
