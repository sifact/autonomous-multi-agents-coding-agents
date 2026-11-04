Write `main.py`, a stack-based (reverse Polish) calculator, run as `python main.py` with no
arguments. It reads UTF-8 expressions from standard input, one per line (lines end at `\n`
only), and answers each on its own line of standard output. Any command-line argument is an
error: print a message on standard error, nothing on standard output, and exit with status 2.

Processing of one input line:

- Split the line into tokens with `str.split()` (any whitespace, so tabs and `\r` are
  separators). A line without tokens is skipped: no output for it.
- A *number* token matches the regular expression `-?[0-9]+(\.[0-9]+)?` completely (ASCII
  digits only; `-3`, `2.50` and `007` are numbers; `+5`, `.5`, `5.`, `1e3`, `nan` are not).
  It is converted with `float()` and pushed on the stack.
- Operators work on the stack, left to right. `+ - * / ^`: pop `b`, pop `a`, push `a op b`
  (`^` is `a ** b`; for `a b -` the result is `a - b`). `neg` negates the top value, `dup`
  pushes a copy of the top value, `swap` exchanges the top two values.
- Any other token is an error `bad token: <token>`.
- Processing stops at the first error in the line, so later tokens are never looked at.
  The possible errors, as printed after the prefix `error: `, are:
  - `bad token: <token>` for an unknown token;
  - `stack underflow` when an operator needs more values than the stack has;
  - `division by zero` for `/` when `b` is 0;
  - `invalid power` when `^` raises an exception (for example `0 -1 ^`, or an overflow like
    `10 1000 ^`) or would give a complex number (for example `-8 0.5 ^`);
  - `overflow` when any other operation produces a result that is not finite (a number token
    too large for a float counts too);
  - `too many values` when, after the last token, more than one value is left on the stack.
- If there is no error, the single value left is the result.

Output, one line per non-skipped input line, in order: the result, or `error: <message>`
(on standard output, e.g. `error: stack underflow`). A result that is a whole number
(`float.is_integer()`) is printed as an integer, so `-0.0` prints `0` and `1e12` prints
`1000000000000`; any other result is printed with `f"{result:.6g}"`.

The exit status is 0 when every line succeeded (including empty input) and 1 when at least
one line printed an error. Every output line ends with `\n`.
