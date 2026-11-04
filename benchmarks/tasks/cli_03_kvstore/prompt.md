Write `main.py`, a tiny persistent key-value store, run as
`python main.py [--file PATH] COMMAND [ARGS...]`.

State lives in a JSON file: `--file PATH` if given (it comes before the command), otherwise
`store.json` in the current directory. `--file` is only recognised as the very first argument
(it needs a value, else exit 2); every later argument is a plain value, even if it starts
with `-` (so `set mode -v` stores `-v`). The file holds one JSON object mapping string keys to
string values, e.g. `{"name": "Ada", "port": "8080"}`. Read and write it as UTF-8. A file that
does not exist is an empty store.

Commands (keys and values are command-line arguments, always stored as strings, so
`set port 8080` stores `"8080"`):

- `set KEY VALUE`: store the value, replacing any old value, keep all other keys, print
  nothing, exit 0. `KEY` must not be empty (exit 2); `VALUE` may be the empty string.
- `get KEY`: print the value followed by `\n`, exit 0.
- `del KEY`: remove the key, print nothing, exit 0.
- `list`: print one `KEY=VALUE` line per entry, sorted by key in plain string (code point)
  order; an empty store prints nothing.

Rules for the file:

- `set` creates the file when needed. `get`, `list` and every failing command never create or
  change the file (not even its formatting: it stays byte for byte as it was). Removing the
  last key leaves `{}` in the file.

Errors print nothing on standard output, put a message starting with `error:` on standard
error, and exit with a status code:

- 1: `get` or `del` of a key that is not in the store (the message names the key);
- 2: no command, an unknown command, or the wrong number of arguments for a command, or an
  empty `KEY`;
- 3: the file exists but is not valid JSON, or is not an object whose values are all strings.
  This applies to every command, and the file is left byte-for-byte unchanged.
