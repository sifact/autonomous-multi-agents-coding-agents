"""Groq chat model with 429 backoff and a requests-per-minute limiter.

The network call is an injectable function so retry/limiter logic is testable offline.
"""
import random
import threading
import time
from collections import deque
from collections.abc import Callable

from coding_agent.llm.base import LLMResponse, Usage

_WINDOW_S = 60.0

CallFn = Callable[[str, str, str, str], LLMResponse]  # (model, api_key, system, user)


class MissingApiKeyError(RuntimeError):
    pass


class RateLimited(Exception):
    """HTTP 429 from the provider; retry_after is seconds if the server said so."""

    def __init__(self, retry_after: float | None = None) -> None:
        super().__init__(f"rate limited (retry_after={retry_after})")
        self.retry_after = retry_after


def _retry_after(exc: Exception) -> float | None:
    headers = getattr(getattr(exc, "response", None), "headers", None)
    try:
        return float(headers["retry-after"]) if headers and "retry-after" in headers else None
    except (TypeError, ValueError):
        return None


def _content_text(content: object) -> str:
    """Flatten a message's content (str or list of parts) to plain text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part if isinstance(part, str) else str(part.get("text", ""))
            for part in content
            if isinstance(part, (str, dict))
        )
    return str(content)


class RateLimiter:
    """Sliding 60-second window; share one across models since Groq limits per key."""

    def __init__(
        self,
        max_rpm: int,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if max_rpm < 1:
            raise ValueError(f"max_rpm must be >= 1, got {max_rpm}")
        self.max_rpm = max_rpm
        self._clock, self._sleep = clock, sleep
        self._sent: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = self._clock()
                while self._sent and self._sent[0] <= now - _WINDOW_S:
                    self._sent.popleft()
                if len(self._sent) < self.max_rpm:
                    self._sent.append(now)
                    return
                wait = self._sent[0] + _WINDOW_S - now
            self._sleep(wait)  # outside the lock so other threads can check the window


def _langchain_call(model: str, api_key: str, system: str, user: str) -> LLMResponse:
    """Real call through langchain-groq; maps the SDK's 429 to RateLimited."""
    import groq
    from langchain_groq import ChatGroq

    # max_retries=0: retries are ours, so the limiter and backoff stay in control.
    chat = ChatGroq(model=model, api_key=api_key, temperature=0, max_retries=0)  # type: ignore[arg-type]
    try:
        msg = chat.invoke([("system", system), ("human", user)])
    except groq.RateLimitError as exc:
        raise RateLimited(_retry_after(exc)) from exc
    meta = getattr(msg, "usage_metadata", None) or {}
    return LLMResponse(_content_text(msg.content), Usage(meta.get("input_tokens", 0), meta.get("output_tokens", 0)))


class GroqChatModel:
    def __init__(
        self,
        model: str,
        api_key: str | None,
        *,
        max_rpm: int | None = None,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        limiter: RateLimiter | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        jitter: Callable[[], float] = random.random,
        call: CallFn = _langchain_call,
    ) -> None:
        if not api_key:
            raise MissingApiKeyError("GROQ_API_KEY is not set; add it to the environment or .env")
        self.model = model
        self._api_key = api_key
        if max_rpm is not None and limiter is not None:
            raise ValueError("pass either max_rpm or limiter, not both")
        self._limiter = limiter or (
            RateLimiter(max_rpm, clock=clock, sleep=sleep) if max_rpm is not None else None
        )
        self._max_delay = max_delay
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._sleep, self._clock, self._jitter, self._call = sleep, clock, jitter, call

    def __repr__(self) -> str:
        return f"GroqChatModel(model={self.model!r})"

    def invoke(self, system: str, user: str) -> LLMResponse:
        for attempt in range(self._max_retries + 1):
            if self._limiter is not None:
                self._limiter.acquire()
            try:
                return self._call(self.model, self._api_key, system, user)
            except RateLimited as exc:
                if attempt == self._max_retries:
                    raise
                if exc.retry_after is not None:
                    if exc.retry_after > self._max_delay:
                        raise  # too long to wait here; let the caller record it
                    delay = exc.retry_after
                else:
                    step = self._base_delay * 2**attempt
                    delay = min(step + self._jitter() * step, self._max_delay)
                self._sleep(delay)
        raise AssertionError("unreachable")
