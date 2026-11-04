"""Notional $ per million tokens, used to report cost even on Groq's free tier.

Source checked 2026-11-05: https://groq.com/pricing and
https://console.groq.com/docs/models. The pricing page showed no per-token list price
for llama-3.1-8b-instant or llama-3.3-70b-versatile (only "Contact Sales"), so those
are None rather than guessed. Fill in from the page when a price is published.
"""
from dataclasses import dataclass

from coding_agent.llm.base import Usage


@dataclass(frozen=True)
class Price:
    input_per_m: float
    output_per_m: float


PRICES: dict[str, Price | None] = {
    "llama-3.1-8b-instant": None,
    "llama-3.3-70b-versatile": None,
}


def cost_usd(model: str, usage: Usage) -> float | None:
    """Notional cost in USD, or None when the model's price is unknown."""
    price = PRICES.get(model)
    if price is None:
        return None
    return (usage.tokens_in * price.input_per_m + usage.tokens_out * price.output_per_m) / 1_000_000
