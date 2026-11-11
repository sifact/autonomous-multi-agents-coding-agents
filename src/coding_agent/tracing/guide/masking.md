# masking.py

Builds the function that redacts secrets from everything sent to Langfuse.

- `make_mask(secrets)` returns the callable passed as `Langfuse(mask=...)`; it runs on every input, output and metadata value.
- Strings lose Groq keys (`gsk_...`), `sk-...` keys including Langfuse secret keys, `pk-lf-...` public keys, `Authorization:` header lines and bare `Bearer` tokens.
- The exact configured key values are also removed, so an unusual key shape cannot slip through.
- Dicts, lists and tuples are walked recursively and values under keys such as `authorization`, `api_key`, `token` or `password` are replaced outright.
- The input is never mutated and ordinary text or code (for example `task-management-system`) is left untouched.
