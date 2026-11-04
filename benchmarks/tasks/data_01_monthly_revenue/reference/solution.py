import csv
from collections import defaultdict


def monthly_revenue(path: str) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            qty, price = row["quantity"].strip(), row["unit_price"].strip()
            if not qty or not price:
                continue
            totals[row["date"][:7]] += int(qty) * float(price)
    return {month: round(totals[month], 2) for month in sorted(totals)}
