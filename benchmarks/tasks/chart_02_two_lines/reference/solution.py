import csv

from matplotlib.figure import Figure


def build_figure(rows: list[tuple[int, float, float]]) -> Figure:
    fig = Figure(figsize=(8, 4.5))
    ax = fig.add_subplot()
    days = [row[0] for row in rows]
    ax.plot(days, [row[1] for row in rows], label="Online")
    ax.plot(days, [row[2] for row in rows], label="Store")
    ax.legend()
    ax.set_title("Daily Sales")
    ax.set_xlabel("Day")
    ax.set_ylabel("Units sold")
    return fig


def read_rows(csv_path: str) -> list[tuple[int, float, float]]:
    with open(csv_path, encoding="utf-8", newline="") as handle:
        rows = [
            (int(r["day"]), float(r["online"]), float(r["store"]))
            for r in csv.DictReader(handle)
        ]
    return sorted(rows, key=lambda row: row[0])


def save_chart(csv_path: str, png_path: str) -> dict:
    rows = read_rows(csv_path)
    build_figure(rows).savefig(png_path, dpi=100)
    online = round(sum(row[1] for row in rows), 2)
    store = round(sum(row[2] for row in rows), 2)
    leader = "online" if online > store else "store" if store > online else "tie"
    return {"days": len(rows), "online_total": online, "store_total": store, "leader": leader}
