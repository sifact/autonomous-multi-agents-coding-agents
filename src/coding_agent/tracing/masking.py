"""Redaction applied to everything sent to Langfuse, so secrets never leave the machine.

``make_scrubber`` builds the string scrubber; ``make_mask`` walks arbitrary data with it
(the SDK's ``mask=`` hook), and ``scrub_spans`` applies it to exported span fields.
"""
from __future__ import annotations

import dataclasses
import re
from collections.abc import Callable, Iterable
from typing import Any, Protocol

REDACTED = "[REDACTED]"
SECRET_PLACEHOLDER = "<secret>"
SPLIT_KEY_NOTE = "[REDACTED: key-like text split across lines]"

# Key-shaped tokens. No word boundary on the prefixes on purpose: a key glued to other word
# characters (``KEY_gsk_...``, ``xsk-...``) must still go. ``sk-`` needs a long tail so ordinary
# hyphenated words ("task-management-system") are left alone; a rare false positive is fine.
_TOKEN_PATTERNS = (
    re.compile(r"gsk_[A-Za-z0-9]{8,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"pk-lf-[A-Za-z0-9-]{8,}"),
)
# "Authorization: <scheme> <credentials>" up to the end of the line, and bare bearer tokens.
_AUTH_HEADER = re.compile(r"(?i)\bauthorization\b\s*[:=]\s*[^\r\n]*")
_BEARER = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}")
_LINE_BREAK = re.compile(r"\s*[\r\n]\s*")
_SENSITIVE_KEYS = frozenset({"authorization", "api_key", "apikey", "secret", "password", "token"})
_MIN_SECRET_LEN = 6  # shorter configured "secrets" would mangle ordinary text
_MAX_DEPTH = 40

Scrubber = Callable[[str], str]


class MaskFunction(Protocol):
    def __call__(self, *, data: Any, **kwargs: Any) -> Any: ...


def make_scrubber(secrets: Iterable[str] = ()) -> Scrubber:
    """Return ``scrub(text) -> text`` removing key-shaped tokens and the exact secrets.

    Why literals too: the configured keys must go even if their shape ever changes.
    Why a joined pass: a key broken over several lines slips past line-local regexes, so
    if removing the line breaks reveals one, the whole string is replaced (fail closed).
    """
    literals = sorted({s for s in secrets if s and len(s) >= _MIN_SECRET_LEN}, key=len,
                      reverse=True)

    def scrub_once(text: str) -> str:
        for literal in literals:
            text = text.replace(literal, REDACTED)
        text = _AUTH_HEADER.sub(f"Authorization: {REDACTED}", text)
        text = _BEARER.sub(f"Bearer {REDACTED}", text)
        for pattern in _TOKEN_PATTERNS:
            text = pattern.sub(REDACTED, text)
        return text

    def leaks(text: str) -> bool:
        return any(lit in text for lit in literals) or any(p.search(text) for p in _TOKEN_PATTERNS)

    def scrub(text: str) -> str:
        cleaned = scrub_once(text)
        if "\n" in cleaned or "\r" in cleaned:
            joined = _LINE_BREAK.sub("", cleaned)
            if joined != cleaned and leaks(joined):
                return SPLIT_KEY_NOTE
        return cleaned

    return scrub


def make_mask(secrets: Iterable[str] = ()) -> MaskFunction:
    """Build the function handed to ``Langfuse(mask=...)`` (inputs, outputs, metadata)."""
    scrub = make_scrubber(secrets)

    def walk(value: Any, path: frozenset[int], depth: int) -> Any:
        if value is None or isinstance(value, (bool, int, float)):
            return value
        if isinstance(value, str):
            return scrub(value)
        if depth > _MAX_DEPTH or id(value) in path:
            return "[cycle or too deep]"
        inner = path | {id(value)}
        nxt = depth + 1
        if isinstance(value, (bytes, bytearray)):
            return scrub(bytes(value).decode("utf-8", errors="replace"))
        if hasattr(value, "get_secret_value"):  # pydantic SecretStr / SecretBytes
            return SECRET_PLACEHOLDER
        if isinstance(value, dict):
            return {
                scrub(k) if isinstance(k, str) else scrub(str(k)):
                    REDACTED if str(k).lower() in _SENSITIVE_KEYS and v else walk(v, inner, nxt)
                for k, v in value.items()
            }
        if isinstance(value, (list, tuple)):
            return type(value)(walk(v, inner, nxt) for v in value)
        if isinstance(value, (set, frozenset)):
            return [walk(v, inner, nxt) for v in value]  # sets are not JSON: emit a list
        if dataclasses.is_dataclass(value) and not isinstance(value, type):
            fields = {f.name: getattr(value, f.name, None) for f in dataclasses.fields(value)}
            return walk(fields, inner, nxt)
        dump = getattr(value, "model_dump", None)
        if callable(dump):
            try:
                return walk(dump(), inner, nxt)
            except Exception:  # noqa: BLE001, S110
                pass
        return scrub(str(value))

    def mask(*, data: Any, **_: Any) -> Any:
        return walk(data, frozenset(), 0)

    return mask
