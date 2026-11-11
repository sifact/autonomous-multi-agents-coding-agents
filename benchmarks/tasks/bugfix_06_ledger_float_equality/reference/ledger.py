"""Checks on lists of money amounts (credits positive, debits negative)."""


def balance(entries: list[float]) -> float:
    """Total of the entries, rounded to whole cents."""
    return round(sum(entries), 2)


def is_balanced(entries: list[float]) -> bool:
    """True when the credits and debits cancel out."""
    return balance(entries) == 0


def largest_imbalance(batches: dict[str, list[float]]) -> str | None:
    """Name of the batch whose total is furthest from zero.

    The first such batch wins a tie; None when every batch is balanced.
    """
    worst, worst_size = None, 0.0
    for name, entries in batches.items():
        size = abs(balance(entries))
        if size > worst_size:
            worst, worst_size = name, size
    return worst
