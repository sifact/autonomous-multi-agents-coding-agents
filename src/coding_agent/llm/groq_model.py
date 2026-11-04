"""Groq chat model with 429 backoff and a requests-per-minute limiter.

The network call is an injectable function so retry/limiter logic is testable offline.
"""
import random
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
    text = msg.content if isinstance(msg.content, str) else str(msg.content)
    return LLMResponse(text, Usage(meta.get("input_tokens", 0), meta.get("output_tokens", 0)))


class GroqChatModel:
    def __init__(
        self,
        model: str,
        api_key: str | None,
        *,
        max_rpm: int | None = None,
        max_retries: int = 5,
        base_delay: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        jitter: Callable[[], float] = random.random,
        call: CallFn = _langchain_call,
    ) -> None:
        if not api_key:
            raise MissingApiKeyError("GROQ_API_KEY is not set; add it to the environment or .env")
        self.model = model
        self._api_key = api_key
        self._max_rpm = max_rpm
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._sleep, self._clock, self._jitter, self._call = sleep, clock, jitter, call
        self._sent: deque[float] = deque()

    def __repr__(self) -> str:
        return f"GroqChatModel(model={self.model!r})"

    def _throttle(self) -> None:
        if self._max_rpm is None:
            return
        now = self._clock()
        while self._sent and self._sent[0] <= now - _WINDOW_S:
            self._sent.popleft()
        if len(self._sent) >= self._max_rpm:
            self._sleep(self._sent[0] + _WINDOW_S - now)
            now = self._clock()
            while self._sent and self._sent[0] <= now - _WINDOW_S:
                self._sent.popleft()
        self._sent.append(now)

    def invoke(self, system: str, user: str) -> LLMResponse:
        for attempt in range(self._max_retries + 1):
            self._throttle()
            try:
                return self._call(self.model, self._api_key, system, user)
            except RateLimited as exc:
                if attempt == self._max_retries:
                    raise
                if exc.retry_after is not None:
                    delay = exc.retry_after
                else:
                    step = self._base_delay * 2**attempt
                    delay = step + self._jitter() * step
                self._sleep(delay)
        raise AssertionError("unreachable")
