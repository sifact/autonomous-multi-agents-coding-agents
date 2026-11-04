import re


def grep_context(path: str, pattern: str, before: int = 0, after: int = 0) -> list[str]:
    if before < 0 or after < 0:
        raise ValueError("before and after must be non-negative")
    regex = re.compile(pattern)
    with open(path, encoding="utf-8", newline="") as f:
        lines = f.read().split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    matches = {i for i, line in enumerate(lines) if regex.search(line)}
    shown: set[int] = set()
    for i in matches:
        shown.update(range(max(0, i - before), min(len(lines), i + after + 1)))
    out: list[str] = []
    previous = None
    for i in sorted(shown):
        if previous is not None and i != previous + 1:
            out.append("--")
        out.append(f"{i + 1}{':' if i in matches else '-'}{lines[i]}")
        previous = i
    return out
