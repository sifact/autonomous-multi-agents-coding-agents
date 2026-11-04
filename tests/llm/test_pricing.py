from coding_agent.llm import Usage, cost_usd, pricing


def test_known_model_cost(monkeypatch):
    monkeypatch.setitem(pricing.PRICES, "m", pricing.Price(input_per_m=0.5, output_per_m=1.5))
    assert cost_usd("m", Usage(2_000_000, 1_000_000)) == 1.0 + 1.5


def test_unknown_model_is_none():
    assert cost_usd("no-such-model", Usage(1, 1)) is None


def test_unverified_default_models_are_none_not_invented():
    # Prices could not be verified from Groq's pages; never guess.
    assert cost_usd("llama-3.1-8b-instant", Usage(1000, 1000)) is None
    assert cost_usd("llama-3.3-70b-versatile", Usage(1000, 1000)) is None
