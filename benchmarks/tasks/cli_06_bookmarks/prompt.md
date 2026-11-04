Write `main.py`, a bookmark manager, run as `python main.py COMMAND [ARGS...]`.

State is kept in `bookmarks.json` in the current directory (UTF-8), one JSON object:

    {"next_id": 3, "items": [{"id": 1, "url": "https://a.example", "title": "A",
                              "tags": ["news", "tech"]}]}

`items` is in ascending `id` order, ids start at 1 and are never reused (`next_id` is the id
of the next new bookmark). A missing file is `{"next_id": 1, "items": []}`.

Commands:

- `add URL [--title TITLE] [--tag TAG]...` (`--tag` may be repeated, options may come before
  or after `URL`). `URL` is stripped and must not be empty. The title defaults to the
  stripped URL. Each tag is stripped and lowercased; an empty tag is an error; duplicate tags
  are dropped, keeping the first occurrence order. Print `added <id>`.
  If a bookmark with the same URL (exact string comparison) already exists, do not add a
  second one: keep its title, append the new tags it does not yet have (in the order given),
  and print `exists <id>`. Both outcomes exit 0.
- `list [--tag TAG]`: one line per bookmark in id order, with four tab-separated fields
  `<id>\t<title>\t<url>\t<tags>` where `<tags>` is the stored tags joined by `,` (an empty
  string when there are none, so the line then ends with a tab). With `--tag` only bookmarks
  that have that tag are shown; the given tag is stripped and lowercased first. If there is
  nothing to show, print nothing.
- `rm ID`: delete the bookmark and print `removed <id>`.
- `tags`: print `<tag> <count>` for every tag in use, sorted by count descending, then tag
  ascending in plain string order. No tags prints nothing.

Every output line ends with `\n`. Only `add` and `rm` write the file; other commands and
failing commands leave it byte for byte untouched, even if it is formatted by hand (and
never create it). The URL is stripped before the duplicate check, so `add u` followed by
`add "  u  "` prints `exists 1`.

Errors print nothing on standard output, put a message on standard error and exit with a
status code:

- 1: `rm` with an unknown id (message `error: no such id: <id>`);
- 2: no command, unknown command, missing/extra arguments, an `ID` that is not a positive
  integer, an empty URL, an empty tag;
- 3: `bookmarks.json` exists but is not valid JSON or lacks the shape above (any command;
  the file is left unchanged).
