import csv

from matplotlib.figure import Figure


def fit(rows: list[tuple[float, float]]) -> tuple[float, float, float]:
    """Return (slope, intercept, r_squared) of the least-squares line."""
    if len(rows) < 2:
        raise ValueError("need at least two points")
    mean_x = sum(x for x, _ in rows) / len(rows)
    mean_y = sum(y for _, y in rows) / len(rows)
    sxx = sum((x - mean_x) ** 2 for x, _ in rows)
    if sxx == 0:
        raise ValueError("all x values are equal")
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in rows)
    slope = sxy / sxx
    intercept = mean_y - slope * mean_x
    ss_tot = sum((y - mean_y) ** 2 for _, y in rows)
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in rows)
    return slope, intercept, 1.0 if ss_tot == 0 else 1 - ss_res / ss_tot


def build_figure(rows: list[tuple[float, float]]) -> Figure:
    slope, intercept, _ = fit(rows)
    xs = [x for x, _ in rows]
    ends = [min(xs), max(xs)]
    fig = Figure(figsize=(7, 5))
    ax = fig.add_subplot()
    ax.scatter(xs, [y for _, y in rows], label="Data")
    ax.plot(ends, [slope * x + intercept for x in ends], label="Fit")
    ax.legend()
    ax.set_title("Study Hours vs Exam Score")
    ax.set_xlabel("Hours studied")
    ax.set_ylabel("Exam score")
    return fig


def read_rows(csv_path: str) -> list[tuple[float, float]]:
    with open(csv_path, encoding="utf-8", newline="") as handle:
        return [
            (float(r["hours"]), float(r["score"]))
            for r in csv.DictReader(handle)
            if r["hours"].strip() and r["score"].strip()
        ]


def save_chart(csv_path: str, png_path: str) -> dict:
    rows = read_rows(csv_path)
    build_figure(rows).savefig(png_path, dpi=100)
    slope, intercept, r_squared = fit(rows)
    return {
        "n": len(rows),
        "slope": round(slope, 3),
        "intercept": round(intercept, 3),
        "r_squared": round(r_squared, 3),
    }
