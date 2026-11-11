"""Scan log lines and pick out the ones that need attention."""

LEVELS = ("WARN", "ERROR")


def _level(line: str) -> str:
    """First word of a log line (the level), ignoring surrounding whitespace."""
    return line.strip().split(" ", 1)[0]


def collect_problems(lines, found=None):
    """Append every WARN or ERROR line (stripped) to found and return found."""
    if found is None:
        found = []
    for line in lines:
        if _level(line) in LEVELS:
            found.append(line.strip())
    return found


def count_by_level(lines) -> dict:
    """How many lines carry each level in LEVELS."""
    counts = {level: 0 for level in LEVELS}
    for line in lines:
        level = _level(line)
        if level in counts:
            counts[level] += 1
    return counts
