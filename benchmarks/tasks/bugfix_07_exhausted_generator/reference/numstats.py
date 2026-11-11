"""Summarise numbers read from text lines, such as a file of measurements."""


def parse_numbers(lines):
    """Lazily turn every non-blank line into a float."""
    return (float(line) for line in lines if line.strip())


def summarize(lines) -> dict:
    """count, min, max and mean of the numbers in lines (any iterable of strings)."""
    numbers = list(parse_numbers(lines))
    if not numbers:
        return {"count": 0, "min": None, "max": None, "mean": None}
    return {
        "count": len(numbers),
        "min": min(numbers),
        "max": max(numbers),
        "mean": sum(numbers) / len(numbers),
    }
