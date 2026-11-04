import csv

import numpy as np
from matplotlib.figure import Figure

DEFAULT_EDGES = [0, 20, 40, 60, 80, 100]


def build_figure(rows: list[float], edges: list[float] | None = None) -> Figure:
    bins = list(DEFAULT_EDGES if edges is None else edges)
    if len(bins) < 2 or any(b <= a for a, b in zip(bins, bins[1:])):
        raise ValueError("edges must be strictly increasing with at least two values")
    fig = Figure(figsize=(8, 4.5))
    ax = fig.add_subplot()
    ax.hist(rows, bins=bins)
    ax.set_title("Exam Scores")
    ax.set_xlabel("Score")
    ax.set_ylabel("Students")
    return fig


def read_scores(csv_path: str) -> list[float]:
    with open(csv_path, encoding="utf-8", newline="") as handle:
        return [float(r["score"]) for r in csv.DictReader(handle) if r["score"].strip()]


def save_chart(csv_path: str, png_path: str) -> dict:
    scores = read_scores(csv_path)
    build_figure(scores).savefig(png_path, dpi=100)
    counts, _ = np.histogram(scores, bins=DEFAULT_EDGES)
    mean = round(sum(scores) / len(scores), 2) if scores else None
    return {
        "counts": [int(c) for c in counts],
        "edges": list(DEFAULT_EDGES),
        "outside": len(scores) - int(counts.sum()),
        "mean": mean,
    }
