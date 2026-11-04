# groq_model.py

Groq chat client that adds rate-limit protection around one injectable network call.

- Fails at construction with `MissingApiKeyError` when no API key is given, never at import.
- Retries only HTTP 429 (`RateLimited`); backoff is `base_delay * 2**attempt` plus jitter, capped at `max_delay`.
- A server `Retry-After` is honored if within `max_delay`; a longer one raises `RateLimited` at once so the caller can record it.
- `RateLimiter` is a thread-safe 60-second sliding window (`max_rpm >= 1`) that can be shared across models.
- The real call goes through `langchain-groq` with its own retries disabled; `repr()` never shows the key.
