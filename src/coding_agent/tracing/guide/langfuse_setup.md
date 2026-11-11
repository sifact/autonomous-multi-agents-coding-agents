# langfuse_setup.py

Creates the Langfuse client and callback handler only when both keys are set, and never lets tracing break a run.

- `tracing_enabled` is true only when both the public and the secret key are non-empty; an empty string counts as missing.
- `get_callbacks` returns `[]` when tracing is off or setup fails, otherwise exactly one `CallbackHandler`; Langfuse is imported lazily so the off path starts no threads and makes no network call.
- `client_kwargs` builds the `Langfuse(...)` arguments: keys, host, both masks, a dedicated tracer provider with the scrubbing processor, and a bounded `timeout` (`LANGFUSE_TIMEOUT`, default 2 s) with short flush settings.
- One client is cached per public key and host, and a failed creation is remembered so it warns once per process; `reset` shuts clients down for tests.
- `flush` sends queued traces before a short-lived process exits and swallows every error, and `tracing_status_line` is the one-line CLI notice that never prints a key.
