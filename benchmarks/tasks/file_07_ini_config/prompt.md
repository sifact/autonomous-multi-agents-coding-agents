Write `solution.py` with a function `load_config(path: str) -> dict`.

It reads the INI-style file at `path` (UTF-8) with the standard library's `configparser` and
returns a plain dict of dicts: `{section_name: {key: value}}`. The sample file `app.ini` is in
the working directory.

- Sections appear under their exact names. The special `[DEFAULT]` section is **not** a
  section of its own; its keys are added to every other section, unless that section sets the
  key itself. A file with no sections (or only `[DEFAULT]`) gives `{}`.
- Keys are lower-cased (`configparser`'s normal behaviour).
- Do not use interpolation: a `%` in a value is just a character.
- Inline comments: a `;` or `#` that is preceded by whitespace starts a comment, which is
  removed together with the whitespace before it. A `;` or `#` inside a word (`a#b`) is kept.
  Full-line comments are ignored as usual.
- Type conversion of each value (after stripping whitespace), checked in this order:
  1. `true`, `yes`, `on` (any letter case) become `True`; `false`, `no`, `off` become `False`.
  2. Text matching exactly an optional `-` followed by digits becomes an `int`
     (`"007"` gives `7`, `"1"` and `"0"` are ints, not booleans).
  3. Text matching exactly an optional `-`, digits, `.`, digits becomes a `float`
     (`"0.75"`, `"-2.50"`). Things like `"5."`, `".5"`, `"+5"`, `"1e3"` and `"1.5.2"` stay strings.
  4. Anything else, including the empty string, stays a string.
- A missing file raises `FileNotFoundError` (note that `ConfigParser.read` silently ignores
  missing files, so open the file yourself).
