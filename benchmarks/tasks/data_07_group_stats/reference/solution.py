import csv


def group_stats(path: str) -> dict[str, dict]:
    scores: dict[str, list[float]] = {}
    missing: dict[str, int] = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            team = row["team"].strip() or "unknown"
            scores.setdefault(team, [])
            missing.setdefault(team, 0)
            raw = row["score"].strip()
            if raw:
                scores[team].append(float(raw))
            else:
                missing[team] += 1
    result = {}
    for team in sorted(scores):
        values = scores[team]
        mean = round(sum(values) / len(values), 2) if values else None
        result[team] = {"count": len(values), "missing": missing[team], "mean": mean}
    return result
