import csv

from matplotlib.figure import Figure


def build_figure(rows: list[tuple[str, float]]) -> Figure:
    fig = Figure(figsize=(8, 4.5))
    ax = fig.add_subplot()
    ax.bar([month for month, _ in rows], [revenue for _, revenue in rows])
    ax.set_title("Monthly Revenue")
    ax.set_xlabel("Month")
    ax.set_ylabel("Revenue (USD)")
    return fig


def read_rows(csv_path: str) -> list[tuple[str, float]]:
    with open(csv_path, encoding="utf-8", newline="") as handle:
        return [
            (row["month"], float(row["revenue"]))
            for row in csv.DictReader(handle)
            if row["revenue"].strip()
        ]


def save_chart(csv_path: str, png_path: str) -> dict:
    rows = read_rows(csv_path)
    build_figure(rows).savefig(png_path, dpi=100)
    best = max(rows, key=lambda row: row[1])[0] if rows else None
    return {
        "months": len(rows),
        "total": round(sum(revenue for _, revenue in rows), 2),
        "best_month": best,
    }
