"""Scrubs the span fields the SDK's ``mask=`` hook never sees, and fails closed.

Two parts, because OpenTelemetry splits the work:
- ``SpanScrubProcessor`` runs when a span ends, BEFORE Langfuse's batch processor queues it
  (it is registered first), and rewrites the name, the status description and every event
  (``exception.message`` / ``exception.stacktrace`` included). Attributes are left to the hook.
- ``make_mask_otel_spans`` is Langfuse's export-stage hook for span attributes
  (``langfuse.observation.status_message``, input/output JSON, metadata, ...).
If a scrub step raises, the field is replaced by a placeholder, never sent raw.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from opentelemetry.sdk.trace import Event, SpanProcessor
from opentelemetry.trace import Status, StatusCode

from coding_agent.tracing.masking import REDACTED, Scrubber

SCRUB_FAILED = "[REDACTED: scrub failed]"


def _scrub_once(scrub: Scrubber, text: str) -> str:
    return scrub(text)


def safe_scrub(scrub: Scrubber, text: str) -> str:
    try:
        return _scrub_once(scrub, text)
    except Exception:  # noqa: BLE001 - fail closed
        return SCRUB_FAILED


def _scrub_value(scrub: Scrubber, value: Any) -> Any:
    if isinstance(value, str):
        return safe_scrub(scrub, value)
    if isinstance(value, (list, tuple)):
        return type(value)(_scrub_value(scrub, v) for v in value)
    return value


def scrub_attributes(scrub: Scrubber, attributes: Mapping[str, Any] | None) -> dict[str, Any]:
    return {k: _scrub_value(scrub, v) for k, v in (attributes or {}).items()}


class SpanScrubProcessor(SpanProcessor):
    def __init__(self, scrub: Scrubber) -> None:
        self._scrub = scrub

    def on_end(self, span: Any) -> None:
        try:
            span._name = safe_scrub(self._scrub, span.name)
            status = span.status
            if status is not None and status.description:
                span._status = Status(status.status_code, safe_scrub(self._scrub,
                                                                      status.description))
            span._events = [
                Event(safe_scrub(self._scrub, ev.name),
                      scrub_attributes(self._scrub, ev.attributes), ev.timestamp)
                for ev in span.events
            ]
        except Exception:  # noqa: BLE001 - fail closed: drop what we could not clean
            for attr, value in (("_name", SCRUB_FAILED), ("_events", []),
                                ("_status", Status(StatusCode.ERROR, SCRUB_FAILED))):
                try:
                    setattr(span, attr, value)
                except Exception:  # noqa: BLE001, S110
                    pass


def make_mask_otel_spans(scrub: Scrubber):
    """The ``Langfuse(mask_otel_spans=...)`` hook: scrub every string attribute."""
    from langfuse.types import MaskOtelSpansResult, OtelSpanPatch

    def mask_otel_spans(*, params: Any) -> Any:
        patches = {}
        for identifier, span in params.spans.items():
            changed = {}
            for key, value in span.attributes.items():
                cleaned = _scrub_value(scrub, value)
                if cleaned != value:
                    changed[key] = cleaned
            if changed:
                patches[identifier] = OtelSpanPatch(set_attributes=changed)
        return MaskOtelSpansResult(span_patches=patches)

    return mask_otel_spans


__all__ = ["REDACTED", "SpanScrubProcessor", "make_mask_otel_spans", "safe_scrub"]
