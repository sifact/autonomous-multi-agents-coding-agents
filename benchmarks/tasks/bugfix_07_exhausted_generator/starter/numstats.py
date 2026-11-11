"""Summarise numbers read from text lines, such as a file of measurements."""


def parse_numbers(lines):
    """Lazily turn every non-blank line into a float."""
    return (float(line) for line in lines if line.strip())


def summarize(lines) -> dict:
    """count, min, max and mean of the numbers in lines (any iterable of strings)."""
    numbers = parse_numbers(lines)
    total = 0.0
    count = 0
    for value in numbers:
        total += value
        count += 1
    if count == 0:
        return {"count": 0, "min": None, "max": None, "mean": None}
    return {"count": count, "min": min(numbers), "max": max(numbers), "mean": total / count}
