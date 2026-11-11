"""Keep the published results inside a marked block of the README.

The block sits between ``<!-- RESULTS:START -->`` and ``<!-- RESULTS:END -->``.
Replacing it is idempotent (same table in, same file out) and the write is atomic
(temp file in the same directory, then rename), so an interrupted run never leaves
half a README. Odd marker layouts are refused rather than guessed at, because a
wrong guess would overwrite hand-written text.
"""
import contextlib
import os
import re
import shutil
import tempfile
from pathlib import Path

START = "<!-- RESULTS:START -->"
END = "<!-- RESULTS:END -->"
_STATUS_HEADING = re.compile(r"^## Status\s*$", re.MULTILINE)


class ReadmeMarkerError(ValueError):
    """The README has the results markers in a layout we will not edit."""


def _block(markdown: str) -> str:
    return f"{START}\n{markdown.rstrip()}\n{END}"


def replace_block(text: str, markdown: str) -> str:
    """README text with the results block set to ``markdown`` (section created if absent)."""
    starts, ends = text.count(START), text.count(END)
    if starts == 0 and ends == 0:
        section = f"## Results\n\n{_block(markdown)}\n\n"
        found = _STATUS_HEADING.search(text)
        if found:
            return text[:found.start()] + section + text[found.start():]
        return text.rstrip("\n") + "\n\n" + section.rstrip("\n") + "\n"
    if starts != 1 or ends != 1 or text.index(START) > text.index(END):
        raise ReadmeMarkerError(
            f"README results markers are not exactly one {START} followed by one {END}; "
            "fix or remove them, then run again"
        )
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    return head + _block(markdown) + tail


def write_readme_block(path: Path, markdown: str) -> None:
    """Rewrite the results block of ``path`` atomically; raises ReadmeMarkerError untouched."""
    new_text = replace_block(path.read_text(), markdown)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(new_text)
        shutil.copymode(path, tmp)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise
