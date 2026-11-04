# pricing.py

Per-million-token price table that turns token usage into a notional dollar cost.

- `PRICES` maps a model name to a `Price` (input and output USD per million tokens) or `None`.
- Both default Groq models are `None` because Groq's pages showed no verifiable list price (checked 2026-11-05).
- `cost_usd(model, usage)` returns `None` for unknown or unpriced models, never a guess.
- Cost is notional: it shows what the run would cost even while on the free tier.
- Update the table and its source comment together when Groq publishes prices.
