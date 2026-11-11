`settings.py` has a bug: building settings for one user changes the built-in `DEFAULTS`, so
the next user gets the previous user's choices.

Example: after `build_settings({"editor": {"tabs": 2}})` (which correctly returns
`tabs == 2`), `build_settings()["editor"]["tabs"]` returns `2` instead of `4`, because
`DEFAULTS["editor"]["tabs"]` has been overwritten.

Contract (keep every name and signature):

- `merge(base, overrides)` returns a new dict. Where both sides hold a dict for the same key,
  the two dicts are merged key by key (recursively); otherwise the value from `overrides`
  replaces the one in `base` as a whole (so a list is replaced, never concatenated).
  Keys only in `base` or only in `overrides` are kept.
- `merge` never modifies `base` or `overrides`, and the result shares no dict or list with
  either of them: changing something inside the result later must not change `DEFAULTS` or the
  overrides that were passed in.
- `build_settings(overrides=None)` is `merge(DEFAULTS, overrides)` with no overrides meaning
  an empty dict. `DEFAULTS` itself must stay exactly as defined in the file.
- The merged values themselves are already right and must stay right.
