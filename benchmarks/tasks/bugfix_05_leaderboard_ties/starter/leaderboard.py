"""Rank players on a game leaderboard."""


def rank(scores: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """Return (name, points) pairs best first: more points first, then by name."""
    return sorted(scores, key=lambda entry: (entry[1], entry[0]), reverse=True)


def top_names(scores: list[tuple[str, int]], n: int) -> list[str]:
    """Names of the n best players, best first."""
    return [name for name, _ in rank(scores)[:n]]


def format_board(scores: list[tuple[str, int]]) -> str:
    """One line per player, e.g. '1. cy - 12', best first."""
    lines = []
    for position, (name, points) in enumerate(rank(scores), start=1):
        lines.append(f"{position}. {name} - {points}")
    return "\n".join(lines)
