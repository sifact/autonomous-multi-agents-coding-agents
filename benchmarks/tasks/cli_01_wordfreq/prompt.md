Write `main.py`, a command-line word-frequency counter, run as
`python main.py [--top N] [FILE]`. A sample file `essay.txt` is in the working directory.

- Input is UTF-8 text read from `FILE`, or from standard input when `FILE` is omitted or is
  the single character `-`. Read and write with `encoding="utf-8"` explicitly.
- Lowercase the text with `str.lower()`. A *word* is a maximal run of characters for which
  `str.isalnum()` is true; every other character (spaces, punctuation, apostrophes, hyphens,
  underscores) separates words. So `Don't` gives the two words `don` and `t`.
- Print the most frequent words, one per line, as `<count> <word>` (a single space between;
  every line ends with `\n`). Sort by count descending, then by word ascending in plain
  string (code point) order.
- `--top N` limits the output to the first N lines. N must be an integer of at least 1.
  The default is 10. If there are fewer than N distinct words, print them all.
  `--top` may appear before or after `FILE`.
- Empty input (or input without any word) prints nothing and exits with status 0.
- Errors print nothing to standard output, put a message on standard error, and exit with
  status 2: `--top` missing its value, not an integer, or less than 1; a `FILE` that does not
  exist or cannot be read. Success exits with status 0.
