import csv
from collections import defaultdict


def top_customers(path: str, n: int) -> list[tuple[str, float]]:
    totals: dict[str, float] = defaultdict(float)
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            amount = row["amount"].strip()
            if amount:
                totals[row["customer"].strip()] += float(amount)
    if n <= 0:
        return []
    rounded = [(name, round(total, 2)) for name, total in totals.items()]
    rounded.sort(key=lambda item: (-item[1], item[0]))
    return rounded[:n]
