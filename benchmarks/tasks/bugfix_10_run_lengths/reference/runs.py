"""Run-length helpers for sensor readings."""


def run_lengths(values) -> list[tuple]:
    """Group consecutive equal values into (value, length) pairs, in order."""
    runs = []
    current, length = None, 0
    for value in values:
        if length and value == current:
            length += 1
        else:
            if length:
                runs.append((current, length))
            current, length = value, 1
    if length:
        runs.append((current, length))
    return runs


def longest_run(values) -> int:
    """Length of the longest block of equal consecutive values (0 for no values)."""
    return max((length for _, length in run_lengths(values)), default=0)


def is_constant(values) -> bool:
    """True when all values are equal (an empty sequence counts as constant)."""
    return len(run_lengths(values)) <= 1
