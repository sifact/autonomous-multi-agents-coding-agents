`normalize.py` and `contacts.py` make up a small contact book. Names that are the same person's
name written differently are not treated as the same.

Examples: `dedupe([{"name": "Ada Lovelace"}, {"name": "ada   LOVELACE"}])` should keep only the
first contact but keeps both. `find_contact([{"name": "Straße"}], "STRASSE")` should find the
contact but returns `None`.

Contract (keep every name and signature):

- Two names match when they are equal after ignoring upper/lower case (full Unicode case
  folding, so `"Straße"` and `"STRASSE"` match), ignoring leading and trailing whitespace, and
  treating any run of whitespace between words as a single space.
- `normalize_name(name)` returns the name with case folded and whitespace collapsed to single
  spaces, so two names match exactly when their normalised forms are equal.
- `dedupe(contacts)` keeps the first contact of each matching group with its original
  spelling, drops the rest, preserves the order, and does not modify the input list.
- `find_contact(contacts, name)` returns the first contact whose name matches, or `None`.
- `normalize_email` and `initials` already work and must keep working.
