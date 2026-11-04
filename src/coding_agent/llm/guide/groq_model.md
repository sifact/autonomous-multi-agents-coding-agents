# groq_model.py

Groq chat client that adds rate-limit protection around one injectable network call.

- Fails at construction with `MissingApiKeyError` when no API key is given, never at import.
- Retries only HTTP 429 (`RateLimited`), up to `max_retries`; other errors propagate immediately.
- Backoff is `base_delay * 2**attempt` plus jitter, or the server's `Retry-After` value when present.
- `max_rpm` enforces a 60-second sliding window by sleeping until the oldest request ages out.
- The real call goes through `langchain-groq` with its own retries disabled; `repr()` never shows the key.
