import csv


def total(path: str) -> float:
    with open(path, newline="") as f:
        return sum(float(row["amount"]) for row in csv.DictReader(f))
