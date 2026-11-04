import csv
import math


def _quantile(values: list[float], p: float) -> float:
    pos = (len(values) - 1) * p
    lo = math.floor(pos)
    if pos == lo:
        return values[lo]
    return values[lo] + (pos - lo) * (values[lo + 1] - values[lo])


def find_outliers(path: str) -> dict[str, list[float]]:
    groups: dict[str, list[float]] = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            groups.setdefault(row["sensor"], [])
            try:
                value = float(row["value"])
            except ValueError:
                continue
            if math.isfinite(value):
                groups[row["sensor"]].append(value)
    result: dict[str, list[float]] = {}
    for sensor, values in groups.items():
        if not values:
            continue
        ordered = sorted(values)
        q1, q3 = _quantile(ordered, 0.25), _quantile(ordered, 0.75)
        iqr = q3 - q1
        low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        found = [v for v in values if v < low or v > high]
        if found:
            result[sensor] = found
    return result
