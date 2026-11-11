# scrub_spans.py

Scrubs the span fields that the SDK's `mask=` hook never sees, and fails closed.

- `SpanScrubProcessor` runs when a span ends, before Langfuse's own processor queues it, and rewrites the span name, the status description and every event (including `exception.message` and `exception.stacktrace`).
- `make_mask_otel_spans` is Langfuse's export-stage hook and scrubs every string attribute, such as `langfuse.observation.status_message`, input and output JSON, and metadata.
- Both use the same scrubber as `masking.py`, so a key is removed wherever it appears.
- If scrubbing a field raises, the field is replaced with a placeholder and never sent raw.
- It is wired up in `langfuse_setup.client_kwargs` through a dedicated TracerProvider, so it does not depend on global OpenTelemetry state.
