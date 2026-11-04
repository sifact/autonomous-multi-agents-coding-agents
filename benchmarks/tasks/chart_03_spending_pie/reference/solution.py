import csv

from matplotlib.figure import Figure

SMALL_SHARE = 0.05


def slices(rows: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """Order the slices and merge small categories into a trailing ``Other``."""
    if not rows:
        raise ValueError("rows must not be empty")
    total = sum(amount for _, amount in rows)
    big = [row for row in rows if row[1] / total >= SMALL_SHARE]
    small = [row for row in rows if row[1] / total < SMALL_SHARE]
    big.sort(key=lambda row: (-row[1], row[0]))
    if small:
        big.append(("Other", sum(amount for _, amount in small)))
    return big


def build_figure(rows: list[tuple[str, float]]) -> Figure:
    parts = slices(rows)
    fig = Figure(figsize=(8, 6))
    ax = fig.add_subplot()
    ax.pie(
        [amount for _, amount in parts],
        labels=[label for label, _ in parts],
        autopct=lambda pct: f"{pct:.1f}%",
        startangle=90,
        counterclock=False,
    )
    ax.set_title("Spending by Category")
    return fig


def read_rows(csv_path: str) -> list[tuple[str, float]]:
    totals: dict[str, float] = {}
    with open(csv_path, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            totals[row["category"]] = totals.get(row["category"], 0) + float(row["amount"])
    return list(totals.items())


def save_chart(csv_path: str, png_path: str) -> dict:
    rows = read_rows(csv_path)
    build_figure(rows).savefig(png_path, dpi=100)
    total = sum(amount for _, amount in rows)
    return {
        "total": round(total, 2),
        "slices": [
            (label, round(100 * amount / total, 1)) for label, amount in slices(rows)
        ],
    }
