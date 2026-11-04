import groq
import httpx
import pytest

from coding_agent.llm import GroqChatModel, LLMResponse, MissingApiKeyError, Usage
from coding_agent.llm.groq_model import (
    RateLimited,
    RateLimiter,
    _content_text,
    _retry_after,
)


class Clock:
    def __init__(self):
        self.now = 0.0
        self.sleeps: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, s: float) -> None:
        self.sleeps.append(s)
        self.now += s


def make(call, clock=None, **kw):
    clock = clock or Clock()
    kw.setdefault("jitter", lambda: 0.0)
    m = GroqChatModel("m", "secret-key", sleep=clock.sleep, clock=clock.time, call=call, **kw)
    return m, clock


def ok(text="hi"):
    return LLMResponse(text, Usage(1, 1))


def test_missing_key_raises_clear_error_at_construction():
    with pytest.raises(MissingApiKeyError, match="GROQ_API_KEY"):
        GroqChatModel("m", None)
    with pytest.raises(MissingApiKeyError):
        GroqChatModel("m", "")


def test_repr_hides_key():
    m, _ = make(lambda *a: ok())
    assert "secret-key" not in repr(m)
    assert "secret-key" not in str(m)


def test_success_passes_args_to_call():
    seen = []

    def call(model, key, system, user):
        seen.append((model, key, system, user))
        return ok("out")

    m, _ = make(call)
    assert m.invoke("S", "U").text == "out"
    assert seen == [("m", "secret-key", "S", "U")]


def test_exponential_backoff_on_429():
    n = {"i": 0}

    def call(*a):
        n["i"] += 1
        if n["i"] <= 3:
            raise RateLimited()
        return ok()

    m, clock = make(call, max_retries=5, base_delay=1.0)
    assert m.invoke("s", "u").text == "hi"
    assert clock.sleeps == [1.0, 2.0, 4.0]


def test_jitter_added_to_delay():
    n = {"i": 0}

    def call(*a):
        n["i"] += 1
        if n["i"] == 1:
            raise RateLimited()
        return ok()

    m, clock = make(call, base_delay=2.0, jitter=lambda: 0.5)
    m.invoke("s", "u")
    assert clock.sleeps == [2.0 + 0.5 * 2.0]


def test_retry_after_honored():
    n = {"i": 0}

    def call(*a):
        n["i"] += 1
        if n["i"] == 1:
            raise RateLimited(retry_after=7.5)
        return ok()

    m, clock = make(call, base_delay=1.0)
    m.invoke("s", "u")
    assert clock.sleeps == [7.5]


def test_gives_up_after_max_retries():
    calls = {"n": 0}

    def call(*a):
        calls["n"] += 1
        raise RateLimited()

    m, _ = make(call, max_retries=2)
    with pytest.raises(RateLimited):
        m.invoke("s", "u")
    assert calls["n"] == 3


def test_non_429_errors_not_retried():
    calls = {"n": 0}

    def call(*a):
        calls["n"] += 1
        raise ValueError("boom")

    m, clock = make(call)
    with pytest.raises(ValueError):
        m.invoke("s", "u")
    assert calls["n"] == 1 and clock.sleeps == []


def test_max_rpm_sliding_window():
    m, clock = make(lambda *a: ok(), max_rpm=2)
    m.invoke("s", "u")  # t=0
    clock.now = 10
    m.invoke("s", "u")  # t=10
    assert clock.sleeps == []
    m.invoke("s", "u")  # must wait until t=60 (first call leaves window)
    assert clock.sleeps == [50.0]
    assert clock.now == 60.0
    m.invoke("s", "u")  # second call (t=10) left window at 70
    assert clock.sleeps == [50.0, 10.0]


def test_no_limiter_when_max_rpm_none():
    m, clock = make(lambda *a: ok())
    for _ in range(100):
        m.invoke("s", "u")
    assert clock.sleeps == []


def test_retry_after_above_max_delay_raises_immediately():
    def call(*a):
        raise RateLimited(retry_after=3600)

    m, clock = make(call, max_delay=60)
    with pytest.raises(RateLimited) as ei:
        m.invoke("s", "u")
    assert ei.value.retry_after == 3600
    assert clock.sleeps == []


def test_retry_after_within_max_delay_is_slept():
    n = {"i": 0}

    def call(*a):
        n["i"] += 1
        if n["i"] == 1:
            raise RateLimited(retry_after=60)
        return ok()

    m, clock = make(call, max_delay=60)
    m.invoke("s", "u")
    assert clock.sleeps == [60]


def test_exponential_delay_capped_at_max_delay():
    n = {"i": 0}

    def call(*a):
        n["i"] += 1
        if n["i"] <= 6:
            raise RateLimited()
        return ok()

    m, clock = make(call, max_retries=8, base_delay=1.0, max_delay=10.0)
    m.invoke("s", "u")
    assert clock.sleeps == [1.0, 2.0, 4.0, 8.0, 10.0, 10.0]


@pytest.mark.parametrize("j", [0.0, 0.25, 0.5, 0.999])
def test_jittered_delay_bounded(j):
    n = {"i": 0}

    def call(*a):
        n["i"] += 1
        if n["i"] == 1:
            raise RateLimited()
        return ok()

    m, clock = make(call, base_delay=4.0, max_delay=5.0, jitter=lambda: j)
    m.invoke("s", "u")
    assert 4.0 <= clock.sleeps[0] <= 5.0
    assert clock.sleeps[0] == pytest.approx(min(4.0 + j * 4.0, 5.0))


@pytest.mark.parametrize("bad", [0, -1])
def test_max_rpm_must_be_positive(bad):
    with pytest.raises(ValueError, match="max_rpm"):
        GroqChatModel("m", "k", max_rpm=bad)


def test_shared_limiter_blocks_across_models():
    clock = Clock()
    limiter = RateLimiter(2, clock=clock.time, sleep=clock.sleep)
    a = GroqChatModel("a", "k", limiter=limiter, call=lambda *x: ok(), sleep=clock.sleep, clock=clock.time)
    b = GroqChatModel("b", "k", limiter=limiter, call=lambda *x: ok(), sleep=clock.sleep, clock=clock.time)
    a.invoke("s", "u")
    b.invoke("s", "u")
    assert clock.sleeps == []
    a.invoke("s", "u")  # third request in the window, across two models
    assert clock.sleeps == [60.0]


def _rate_limit_error(headers):
    req = httpx.Request("POST", "https://api.groq.com/x")
    resp = httpx.Response(429, headers=headers, request=req)
    return groq.RateLimitError("slow down", response=resp, body=None)


def test_retry_after_header_seconds():
    assert _retry_after(_rate_limit_error({"retry-after": "12"})) == 12.0


def test_retry_after_header_http_date_is_none():
    err = _rate_limit_error({"retry-after": "Wed, 21 Oct 2026 07:28:00 GMT"})
    assert _retry_after(err) is None


def test_retry_after_header_absent_is_none():
    assert _retry_after(_rate_limit_error({})) is None


def test_content_text_joins_list_parts():
    assert _content_text("plain") == "plain"
    assert _content_text(["a", {"type": "text", "text": "b"}, {"type": "image"}]) == "ab"
