"""Maps provider errors to a friendly message and a CLI exit code."""
from __future__ import annotations

AUTH_MESSAGE = "Groq rejected GROQ_API_KEY (401). Check the key in .env."


def is_auth_error(exc: BaseException) -> bool:
    """HTTP 401 from the provider (checked by status code/name, not by importing the SDK)."""
    return (
        getattr(exc, "status_code", None) == 401
        or type(exc).__name__ == "AuthenticationError"
        or any(c.__name__ == "AuthenticationError" for c in type(exc).__mro__)
    )
