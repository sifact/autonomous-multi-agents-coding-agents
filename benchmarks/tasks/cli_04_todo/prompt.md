Write `main.py`, a to-do list manager, run as `python main.py COMMAND [ARGS...]`.

State is kept in `todo.json` in the current directory (UTF-8), one JSON object:

    {"next_id": 3, "items": [{"id": 1, "text": "buy milk", "done": true},
                             {"id": 2, "text": "call Bob", "done": false}]}

`items` is in ascending `id` order; `next_id` is the id the next added item gets. A missing
file is the empty state `{"next_id": 1, "items": []}`. Ids start at 1 and are never reused,
even after `rm` (so `next_id` only ever grows).

Commands (an `ID` argument must consist only of ASCII digits and be at least 1, so `0`, `-1`, `+1`,
` 1`, `1.0` and `²` are invalid and give exit 2):

- `add TEXT...`: the arguments joined with single spaces, then stripped of leading and
  trailing whitespace (inner spacing is kept), become the item text, with `done` false. The
  text must not be empty (exit 2). Print `added <id>`.
- `list [--pending]`: print one line per item, `[ ] <id> <text>` for open items and
  `[x] <id> <text>` for done ones, in id order. With `--pending` only open items are shown.
  If no line would be printed, print `no items` instead.
- `done ID`: mark the item done and print `done <id>`. Marking an already done item is not an
  error: it prints the same line and changes nothing.
- `rm ID`: delete the item and print `removed <id>`.

Output goes to standard output, each line ends with `\n`. The file is written only by
commands that change it (`add`, a first `done`, `rm`); other commands and failing commands
leave it untouched, byte for byte, even if it is formatted by hand (and do not create it).

Errors print nothing on standard output, put a message starting with `error:` on standard
error and exit with a status code:

- 1: `done` or `rm` with an id that does not exist (message `error: no such id: <id>`);
- 2: no command, unknown command, missing/extra arguments, an invalid `ID`, empty text;
- 3: `todo.json` exists but is not valid JSON or does not have the shape above (any command;
  the file is left unchanged).
