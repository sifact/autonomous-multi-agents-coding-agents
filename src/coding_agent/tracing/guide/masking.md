# masking.py

Builds the string scrubber and the data mask that redact secrets from everything sent to Langfuse.

- `make_scrubber(secrets)` returns `scrub(text)`, which removes `gsk_`, `sk-`, `pk-lf-` tokens (even glued to word characters), `Authorization:` lines, `Bearer` tokens and the exact configured keys.
- A key broken over several lines is caught by re-checking the text with line breaks removed; if one shows up, the whole string is replaced.
- `make_mask(secrets)` walks data for the SDK's `mask=` hook: dict keys and values, lists, tuples, sets, bytes, dataclasses, pydantic models, and any other object via `str()`.
- `SecretStr` values become `<secret>`, values under keys such as `api_key` or `token` are replaced, and cycles or very deep data are cut off.
- It never mutates its input and handles a 5 MB string in well under half a second.
