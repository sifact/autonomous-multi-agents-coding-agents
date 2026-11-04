import threading

import pytest

from coding_agent.config import Settings
from coding_agent.llm import FakeLLM, ModelRouter, Usage, UsageTracker, pricing


def make_router(**kw):
    made: list[str] = []

    def factory(model: str):
        made.append(model)
        return FakeLLM(["r"] * 10)

    return ModelRouter(Settings(groq_api_key="k"), factory=factory, **kw), made


def test_role_mapping():
    router, made = make_router()
    for role in ("planner", "architect", "reviewer"):
        router.for_role(role)
    for role in ("coder", "debugger"):
        router.for_role(role)
    assert made == ["llama-3.1-8b-instant"] * 3 + ["llama-3.3-70b-versatile"] * 2


def test_all_strong_ablation():
    router, made = make_router(all_strong=True)
    router.for_role("planner")
    assert made == ["llama-3.3-70b-versatile"]


def test_per_role_override():
    router, made = make_router(overrides={"planner": "custom-model"})
    router.for_role("planner")
    router.for_role("coder")
    assert made == ["custom-model", "llama-3.3-70b-versatile"]


def test_unknown_role_rejected():
    router, _ = make_router()
    with pytest.raises(ValueError, match="role"):
        router.for_role("janitor")  # type: ignore[arg-type]


def test_tracker_records_usage_under_model_name():
    tracker = UsageTracker()
    router, _ = make_router(tracker=tracker)
    router.for_role("planner").invoke("s" * 40, "u" * 40)
    router.for_role("coder").invoke("s" * 40, "u" * 40)
    assert tracker.total_tokens == 2 * 20
    assert set(tracker.by_model) == {"llama-3.1-8b-instant", "llama-3.3-70b-versatile"}
    assert tracker.by_model["llama-3.1-8b-instant"] == Usage(20, 0)


def test_wrapped_model_returns_response_unchanged():
    router, _ = make_router(tracker=UsageTracker())
    assert router.for_role("coder").invoke("s", "u").text == "r"


def test_tracker_sums_and_cost(monkeypatch):
    monkeypatch.setitem(pricing.PRICES, "m", pricing.Price(1.0, 2.0))
    t = UsageTracker()
    t.add("m", Usage(1_000_000, 500_000))
    t.add("m", Usage(1_000_000, 0))
    assert t.total_tokens == 2_500_000
    assert t.total_cost == pytest.approx(3.0)
    assert t.cost_known is True


def test_tracker_unknown_price_counts_zero_and_flags():
    t = UsageTracker()
    t.add("llama-3.1-8b-instant", Usage(100, 50))
    assert t.total_tokens == 150
    assert t.total_cost == 0.0
    assert t.cost_known is False


def test_tracker_empty_cost_known():
    assert UsageTracker().cost_known is True


def test_tracker_thread_safe():
    t = UsageTracker()

    def work():
        for _ in range(1000):
            t.add("m", Usage(1, 1))

    threads = [threading.Thread(target=work) for _ in range(8)]
    [x.start() for x in threads]
    [x.join() for x in threads]
    assert t.total_tokens == 8 * 1000 * 2
