"""Redaction applied to everything sent to Langfuse, so secrets never leave the machine."""
from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any, Protocol

REDACTED = "[REDACTED]"

# Key-shaped tokens (Groq, OpenAI-style incl. Langfuse sk-lf-, Langfuse public pk-lf-).
_TOKEN_PATTERNS = (
    re.compile(r"\bgsk_[A-Za-z0-9]{8,}"),
    re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{7,}"),
    re.compile(r"\bpk-lf-[A-Za-z0-9-]{8,}"),
)
# "Authorization: <scheme> <credentials>" up to the end of the line, and bare bearer tokens.
_AUTH_HEADER = re.compile(r"(?i)\bauthorization\b\s*[:=]\s*[^\r\n]*")
_BEARER = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}")
_SENSITIVE_KEYS = frozenset({"authorization", "api_key", "apikey", "secret", "password", "token"})
_MIN_SECRET_LEN = 6  # shorter configured "secrets" would mangle ordinary text


class MaskFunction(Protocol):
    def __call__(self, *, data: Any, **kwargs: Any) -> Any: ...


def make_mask(secrets: Iterable[str] = ()) -> MaskFunction:
    """Build the function handed to ``Langfuse(mask=...)``.

    Why a closure: the configured keys must be scrubbed even if their shape ever
    changes, so the exact values are matched in addition to the generic patterns.
    """
    literals = sorted({s for s in secrets if s and len(s) >= _MIN_SECRET_LEN}, key=len,
                      reverse=True)

    def scrub_text(text: str) -> str:
        for literal in literals:
            text = text.replace(literal, REDACTED)
        text = _AUTH_HEADER.sub(f"Authorization: {REDACTED}", text)
        text = _BEARER.sub(f"Bearer {REDACTED}", text)
        for pattern in _TOKEN_PATTERNS:
            text = pattern.sub(REDACTED, text)
        return text

    def walk(value: Any) -> Any:
        if isinstance(value, str):
            return scrub_text(value)
        if isinstance(value, dict):
            return {
                k: REDACTED if str(k).lower() in _SENSITIVE_KEYS and v else walk(v)
                for k, v in value.items()
            }
        if isinstance(value, (list, tuple)):
            return type(value)(walk(v) for v in value)
        return value

    def mask(*, data: Any, **_: Any) -> Any:
        return walk(data)

    return mask
