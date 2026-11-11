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
from coding_agent.tracing.masking import make_mask

log = logging.getLogger(__name__)

_clients: dict[tuple[str, str], Any] = {}  # one client (= one export thread) per key and host
_lock = threading.Lock()


def _secret(value: Any) -> str:
    return value.get_secret_value() if value else ""


def tracing_enabled(settings: Settings) -> bool:
    """True when both Langfuse keys are present (an empty string counts as missing)."""
    return bool(_secret(settings.langfuse_public_key) and _secret(settings.langfuse_secret_key))


def client_kwargs(settings: Settings) -> dict[str, Any]:
    """Arguments for ``Langfuse(...)``: keys, host and the secret-scrubbing mask."""
    public, secret = _secret(settings.langfuse_public_key), _secret(settings.langfuse_secret_key)
    return {
        "public_key": public, "secret_key": secret, "base_url": settings.langfuse_host,
        "mask": make_mask([public, secret, _secret(settings.groq_api_key)]),
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
        if key not in _clients:
            try:
                _clients[key] = _new_client(settings)
            except Exception as exc:  # noqa: BLE001 - tracing must never break a run
                log.warning("Langfuse tracing disabled: %s: %s", type(exc).__name__, exc)
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
        log.warning("Langfuse tracing disabled: %s: %s", type(exc).__name__, exc)
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
