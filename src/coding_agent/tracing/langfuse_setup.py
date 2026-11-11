"""Creates the Langfuse client and callback handler, and only when both keys are set.

Langfuse is imported lazily so the disabled path has no import cost, no
background threads and no network. Every function here is failure-safe: tracing
is an add-on and must never break a run.
"""
from __future__ import annotations

import logging
import threading
from typing import Any

from coding_agent.config import Settings
from coding_agent.tracing.masking import Scrubber, make_mask, make_scrubber

log = logging.getLogger(__name__)

_clients: dict[tuple[str, str], Any] = {}  # one client (= one export thread) per key and host
_failed: set[tuple[str, str]] = set()  # keys whose client could not be built: warn once
_lock = threading.Lock()
FLUSH_AT = 64  # spans per export batch (the SDK default is 512)
FLUSH_INTERVAL_S = 1.0  # seconds between background exports (the SDK default is 5)


def _secret(value: Any) -> str:
    return value.get_secret_value() if value else ""


def tracing_enabled(settings: Settings) -> bool:
    """True when both Langfuse keys are present (an empty string counts as missing)."""
    return bool(_secret(settings.langfuse_public_key) and _secret(settings.langfuse_secret_key))


def _secrets(settings: Settings) -> list[str]:
    return [_secret(settings.langfuse_public_key), _secret(settings.langfuse_secret_key),
            _secret(settings.groq_api_key)]


def scrubber_for(settings: Settings) -> Scrubber:
    """The string scrubber for these settings (configured keys plus key-shaped tokens)."""
    return make_scrubber(_secrets(settings))


def client_kwargs(settings: Settings) -> dict[str, Any]:
    """Arguments for ``Langfuse(...)``: keys, host, masking and bounded export timing.

    Our own TracerProvider (not the global one) carries the scrubbing processor, registered
    before Langfuse's, and the seed-proof id generator.
    """
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider

    from coding_agent.tracing.ids import SecureIdGenerator
    from coding_agent.tracing.scrub_spans import SpanScrubProcessor, make_mask_otel_spans

    public, secret = _secret(settings.langfuse_public_key), _secret(settings.langfuse_secret_key)
    scrub = scrubber_for(settings)
    provider = TracerProvider(resource=Resource.create({}), id_generator=SecureIdGenerator())
    provider.add_span_processor(SpanScrubProcessor(scrub))
    return {
        "public_key": public, "secret_key": secret, "base_url": settings.langfuse_host,
        "mask": make_mask(_secrets(settings)),
        "mask_otel_spans": make_mask_otel_spans(scrub),
        "tracer_provider": provider,
        "timeout": settings.langfuse_timeout,
        "flush_at": FLUSH_AT, "flush_interval": FLUSH_INTERVAL_S,
    }


def _new_client(settings: Settings) -> Any:
    from langfuse import Langfuse  # lazy: keeps the disabled path import-free

    return Langfuse(**client_kwargs(settings))


def get_client(settings: Settings) -> Any | None:
    """The shared Langfuse client, or None when tracing is off or setup failed."""
    if not tracing_enabled(settings):
        return None
    key = (_secret(settings.langfuse_public_key), settings.langfuse_host)
    with _lock:
        if key in _failed:
            return None
        if key not in _clients:
            try:
                _clients[key] = _new_client(settings)
            except Exception as exc:  # noqa: BLE001 - tracing must never break a run
                _failed.add(key)
                log.warning("Langfuse tracing disabled: %s: %s", type(exc).__name__,
                            scrubber_for(settings)(str(exc)))
                return None
        return _clients[key]


def get_callbacks(settings: Settings) -> list[Any]:
    """``[]`` when tracing is off or broken, else one configured Langfuse CallbackHandler."""
    client = get_client(settings)
    if client is None:
        return []
    try:
        from langfuse.langchain import CallbackHandler

        return [CallbackHandler(public_key=_secret(settings.langfuse_public_key))]
    except Exception as exc:  # noqa: BLE001
        log.warning("Langfuse tracing disabled: %s: %s", type(exc).__name__,
                    scrubber_for(settings)(str(exc)))
        return []


def flush(target: Any | None = None) -> None:
    """Send queued traces now (short-lived processes exit before the background export).

    ``target`` may be a client or handler-like object with ``flush``; by default every
    client this module created is flushed. Never raises.
    """
    targets = [target] if target is not None else list(_clients.values())
    for item in targets:
        fn = getattr(item, "flush", None)
        if fn is None:
            continue
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            log.warning("Langfuse flush failed: %s: %s", type(exc).__name__, exc)


def reset() -> None:
    """Shut down and forget every client (tests; also frees the export thread)."""
    with _lock:
        clients = list(_clients.values())
        _clients.clear()
        _failed.clear()
    for client in clients:
        try:
            client.shutdown()
        except Exception:  # noqa: BLE001, S110
            pass


def tracing_status_line(settings: Settings) -> str:
    """The one-line CLI notice. Never includes a key."""
    if tracing_enabled(settings):
        return f"Langfuse tracing: on ({settings.langfuse_host.rstrip('/')})"
    return "Langfuse tracing: off (set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY to enable)"
