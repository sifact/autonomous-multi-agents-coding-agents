import csv

from matplotlib.figure import Figure


def pivot(rows: list[tuple[str, str, float]]) -> tuple[list[str], list[str], dict]:
    """Return (quarters in first-seen order, sorted products, units by (quarter, product))."""
    if not rows:
        raise ValueError("rows must not be empty")
    quarters = list(dict.fromkeys(q for q, _, _ in rows))
    products = sorted({p for _, p, _ in rows})
    units: dict[tuple[str, str], float] = {}
    for quarter, product, count in rows:
        units[quarter, product] = units.get((quarter, product), 0) + count
    return quarters, products, units


def build_figure(rows: list[tuple[str, str, float]]) -> Figure:
    quarters, products, units = pivot(rows)
    fig = Figure(figsize=(8, 5))
    ax = fig.add_subplot()
    bottoms = [0.0] * len(quarters)
    for product in products:
        heights = [units.get((q, product), 0) for q in quarters]
        ax.bar(quarters, heights, bottom=bottoms, label=product)
        bottoms = [b + h for b, h in zip(bottoms, heights)]
    ax.legend()
    ax.set_title("Units by Quarter")
    ax.set_xlabel("Quarter")
    ax.set_ylabel("Units")
    return fig


def read_rows(csv_path: str) -> list[tuple[str, str, int]]:
    with open(csv_path, encoding="utf-8", newline="") as handle:
        return [(r["quarter"], r["product"], int(r["units"])) for r in csv.DictReader(handle)]


def save_chart(csv_path: str, png_path: str) -> dict:
    rows = read_rows(csv_path)
    build_figure(rows).savefig(png_path, dpi=100)
    quarters, products, units = pivot(rows)
    by_product = {p: sum(units.get((q, p), 0) for q in quarters) for p in products}
    return {
        "quarters": quarters,
        "products": products,
        "totals": [sum(units.get((q, p), 0) for p in products) for q in quarters],
        "top_product": max(products, key=lambda p: (by_product[p], -products.index(p))),
    }
