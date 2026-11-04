import io
import struct

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402

import solution  # noqa: E402
from solution import build_figure, save_chart  # noqa: E402

SIGNATURE = b"\x89PNG\r\n\x1a\n"


@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close("all")


def png_size(path):
    data = open(path, "rb").read()
    assert data[:8] == SIGNATURE
    length, kind = struct.unpack(">I4s", data[8:16])
    assert kind == b"IHDR" and length == 13
    return struct.unpack(">II", data[16:24])


def drawn(fig):
    fig.savefig(io.BytesIO(), format="png")  # forces tick labels to be computed
    return fig


def check_content(fig, rows):
    assert len(fig.axes) == 1
    ax = fig.axes[0]
    drawn(fig)
    assert ax.get_title() == "Monthly Revenue"
    assert ax.get_xlabel() == "Month"
    assert ax.get_ylabel() == "Revenue (USD)"
    assert [p.get_height() for p in ax.patches] == pytest.approx([r for _, r in rows])
    assert [t.get_text() for t in ax.get_xticklabels()] == [m for m, _ in rows]
    assert ax.get_legend() is None
    assert tuple(fig.get_size_inches()) == pytest.approx((8, 4.5))


def write_csv(tmp_path, text, name="in.csv"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_bars_follow_row_order_and_values():
    rows = [("Mar", 30.0), ("Jan", 10.0), ("Feb", 25.5), ("Apr", 5.0)]
    check_content(build_figure(rows), rows)


def test_other_data_gives_other_chart():
    rows = [("Q4", 1.0), ("Q1", 400.0), ("Q3", 0.0), ("Q2", 399.5), ("Q5", 12.0)]
    check_content(build_figure(rows), rows)
    check_content(build_figure([("Only", 7)]), [("Only", 7)])


def test_bars_are_placed_left_to_right_in_row_order():
    rows = [("b", 2.0), ("a", 1.0), ("c", 3.0)]
    ax = build_figure(rows).axes[0]
    xs = [p.get_x() + p.get_width() / 2 for p in ax.patches]
    assert xs == sorted(xs)
    assert len(set(xs)) == 3


def test_empty_rows_keep_titles_and_have_no_bars():
    fig = build_figure([])
    ax = fig.axes[0]
    assert len(fig.axes) == 1 and len(ax.patches) == 0
    assert ax.get_title() == "Monthly Revenue"
    assert ax.get_xlabel() == "Month"
    assert ax.get_ylabel() == "Revenue (USD)"


def test_save_chart_on_sample_file(tmp_path):
    out = tmp_path / "chart.png"
    summary = save_chart("revenue.csv", str(out))
    assert summary == {"months": 5, "total": 7871.75, "best_month": "Jun"}
    width, height = png_size(out)
    assert (width, height) == (800, 450)
    assert out.stat().st_size > 3000


def test_save_chart_skips_empty_revenue_and_ties_pick_first(tmp_path):
    path = write_csv(tmp_path, "month,revenue\nZed,5\nApr,\nMar,9.5\nAaa,9.5\nMay, \n")
    summary = save_chart(path, str(tmp_path / "t.png"))
    assert summary == {"months": 3, "total": 24.0, "best_month": "Mar"}
    assert set(summary) == {"months", "total", "best_month"}
    assert isinstance(summary["months"], int)


def test_total_is_rounded_once_after_summing(tmp_path):
    path = write_csv(tmp_path, "month,revenue\nA,0.1\nB,0.2\nC,0.005\nD,1e3\n")
    summary = save_chart(path, str(tmp_path / "t.png"))
    assert summary["total"] == round(0.1 + 0.2 + 0.005 + 1000.0, 2)
    assert summary["best_month"] == "D"


def test_save_chart_with_no_rows(tmp_path):
    path = write_csv(tmp_path, "month,revenue\nApr,\n")
    out = tmp_path / "empty.png"
    assert save_chart(path, str(out)) == {"months": 0, "total": 0, "best_month": None}
    assert png_size(out) == (800, 450)


def test_png_depends_on_the_data(tmp_path):
    a = write_csv(tmp_path, "month,revenue\nJan,10\nFeb,20\nMar,5\n", "a.csv")
    b = write_csv(tmp_path, "month,revenue\nJan,5\nFeb,5\nMar,50\n", "b.csv")
    save_chart(a, str(tmp_path / "a.png"))
    save_chart(b, str(tmp_path / "b.png"))
    assert (tmp_path / "a.png").read_bytes() != (tmp_path / "b.png").read_bytes()
    assert png_size(tmp_path / "a.png") == png_size(tmp_path / "b.png") == (800, 450)


def test_save_chart_unicode_months_and_overwrite(tmp_path):
    path = write_csv(tmp_path, "month,revenue\nMärz,3\nJänner,4\n")
    out = tmp_path / "o.png"
    out.write_bytes(b"old")
    assert save_chart(path, str(out))["best_month"] == "Jänner"
    assert out.read_bytes()[:8] == SIGNATURE


def test_png_comes_from_the_figure_returned_by_build_figure(tmp_path, monkeypatch):
    from matplotlib.figure import Figure

    seen = {}

    def fake(rows):
        seen["rows"] = [tuple(r) for r in rows]
        return Figure(figsize=(5, 3))

    monkeypatch.setattr(solution, "build_figure", fake)
    path = write_csv(tmp_path, "month,revenue\nB,2\nA,\nC,3.5\n")
    out = tmp_path / "spy.png"
    solution.save_chart(path, str(out))
    assert seen["rows"] == [("B", 2.0), ("C", 3.5)]
    assert png_size(out) == (500, 300)
