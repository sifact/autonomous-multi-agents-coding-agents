"""Keep the published results inside a marked block of the README.

The block sits between ``<!-- RESULTS:START -->`` and ``<!-- RESULTS:END -->``.
Replacing it is idempotent (same table in, same file out) and the write is atomic
(temp file next to the real file, then rename), so an interrupted run never leaves
half a README.

Safety rules: a marker only counts when it is alone on its line and outside a fenced
code block (``` or ~~~), so examples and quoted prose never get overwritten; the file is
read and written as bytes and the block uses the file's own newline style (CRLF stays
CRLF); a symlinked README is written through to its target and stays a link. Odd marker
layouts are refused rather than guessed at, because a wrong guess would overwrite
hand-written text.
"""
import contextlib
import os
import re
import shutil
import tempfile
from pathlib import Path

START = "<!-- RESULTS:START -->"
END = "<!-- RESULTS:END -->"
_STATUS = "## Status"
_FENCE = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$")


class ReadmeMarkerError(ValueError):
    """The README has the results markers in a layout we will not edit."""


def _scan(lines: list[str]) -> tuple[list[int], list[int], int | None]:
    """Line indexes of lone markers and of the first ``## Status`` heading, outside fences."""
    starts: list[int] = []
    ends: list[int] = []
    status: int | None = None
    fence: tuple[str, int] | None = None
    for i, line in enumerate(lines):
        body = line.rstrip("\r\n")
        match = _FENCE.match(body)
        if fence is None:
            if match:
                fence = (match.group(2)[0], len(match.group(2)))
                continue
        else:
            if match and match.group(2)[0] == fence[0] and len(match.group(2)) >= fence[1] \
                    and not match.group(3).strip():
                fence = None
            continue
        stripped = body.strip()
        if stripped == START:
            starts.append(i)
        elif stripped == END:
            ends.append(i)
        elif status is None and stripped == _STATUS:
            status = i
    return starts, ends, status


def _newline(text: str) -> str:
    crlf = text.count("\r\n")
    return "\r\n" if crlf > text.count("\n") - crlf else "\n"


def replace_block(text: str, markdown: str) -> str:
    """README text with the results block set to ``markdown`` (section created if absent)."""
    lines = text.splitlines(keepends=True)
    nl = _newline(text)
    body = markdown.rstrip().splitlines()
    starts, ends, status = _scan(lines)
    if not starts and not ends:
        section = nl.join(["## Results", "", START, *body, END]) + nl
        if status is not None:
            offset = sum(len(line) for line in lines[:status])
            return text[:offset] + section + nl + text[offset:]
        return text.rstrip("\r\n") + nl + nl + section
    if len(starts) != 1 or len(ends) != 1 or starts[0] > ends[0]:
        raise ReadmeMarkerError(
            f"README results markers are not exactly one {START} followed by one {END} "
            "(each alone on its line, outside code fences); fix or remove them, then run again"
        )
    head = "".join(lines[:starts[0] + 1])
    return head + nl.join(body) + nl + "".join(lines[ends[0]:])


def write_readme_block(path: Path, markdown: str) -> None:
    """Rewrite the results block of ``path`` atomically; raises ReadmeMarkerError untouched."""
    target = Path(os.path.realpath(path))  # a symlinked README is updated through the link
    try:
        text = target.read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ReadmeMarkerError(f"{target} is not valid UTF-8") from exc
    data = replace_block(text, markdown).encode("utf-8")
    fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.", suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        shutil.copymode(target, tmp)
        os.replace(tmp, target)
    except BaseException:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise
