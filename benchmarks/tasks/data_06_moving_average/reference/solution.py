import csv


def moving_average(path: str, window: int) -> list[dict]:
    if window < 1:
        raise ValueError("window must be >= 1")
    with open(path, newline="") as f:
        rows = [(r["date"], float(r["close"])) for r in csv.DictReader(f) if r["close"].strip()]
    result = []
    for i in range(window - 1, len(rows)):
        chunk = rows[i - window + 1 : i + 1]
        mean = sum(close for _, close in chunk) / window
        result.append({"date": rows[i][0], "ma": round(mean, 2)})
    return result
