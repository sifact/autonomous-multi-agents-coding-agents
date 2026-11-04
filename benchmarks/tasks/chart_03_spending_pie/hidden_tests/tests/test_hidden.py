import math
import struct
from collections import Counter

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


def pie_parts(fig):
    """Return [(extent_degrees, mid_angle_degrees)] for the wedges in drawing order."""
    ax = fig.axes[0]
    out = []
    for w in ax.patches:
        out.append((w.theta2 - w.theta1, (w.theta1 + w.theta2) / 2 % 360))
    return out


def angle_of(text):
    x, y = text.get_position()
    return math.degrees(math.atan2(y, x)) % 360


def check_pie(fig, expected):
    """expected: [(label, amount)] in wedge order, amounts already merged."""
    assert len(fig.axes) == 1
    ax = fig.axes[0]
    assert ax.get_title() == "Spending by Category"
    assert ax.get_legend() is None
    assert tuple(fig.get_size_inches()) == pytest.approx((8, 6))
    total = sum(a for _, a in expected)
    parts = pie_parts(fig)
    assert len(parts) == len(expected)
    assert [e for e, _ in parts] == pytest.approx([360 * a / total for _, a in expected])
    pcts = [f"{100 * a / total:.1f}%" for _, a in expected]
    labels = [lab for lab, _ in expected]
    assert Counter(t.get_text() for t in ax.texts) == Counter(labels + pcts)
    for (label, _), pct, (_, mid) in zip(expected, pcts, parts):
        for wanted in (label, pct):
            angles = [angle_of(t) for t in ax.texts if t.get_text() == wanted]
            assert any(min(abs(a - mid), 360 - abs(a - mid)) < 2 for a in angles), wanted


def write_csv(tmp_path, text, name="in.csv"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_slices_sorted_by_amount_descending():
    rows = [("Food", 30), ("Rent", 50), ("Fun", 20)]
    check_pie(build_figure(rows), [("Rent", 50), ("Food", 30), ("Fun", 20)])


def test_small_categories_merge_into_other_placed_last():
    rows = [("A", 60), ("tiny1", 4), ("B", 6), ("tiny2", 4), ("tiny3", 4), ("C", 10),
            ("tiny4", 4), ("tiny5", 4), ("tiny6", 4)]
    # Other = 24 is bigger than C and B but must still come last
    check_pie(build_figure(rows), [("A", 60), ("C", 10), ("B", 6), ("Other", 24)])


def test_share_of_exactly_five_percent_is_not_small():
    check_pie(build_figure([("Big", 95), ("Edge", 5)]), [("Big", 95), ("Edge", 5)])
    rows = [("Big", 94.9), ("Edge", 5.1), ("Low", 0.0001)]
    check_pie(build_figure(rows), [("Big", 94.9), ("Edge", 5.1), ("Other", 0.0001)])
    rows = [("Big", 96), ("Low", 4)]
    check_pie(build_figure(rows), [("Big", 96), ("Other", 4)])


def test_ties_are_broken_by_name_ascending():
    rows = [("Zed", 20), ("Mid", 60), ("Apple", 20)]
    check_pie(build_figure(rows), [("Mid", 60), ("Apple", 20), ("Zed", 20)])


def test_single_category_is_a_full_circle():
    fig = build_figure([("Only", 12.5)])
    check_pie(fig, [("Only", 12.5)])
    assert [t.get_text() for t in fig.axes[0].texts if t.get_text().endswith("%")] == ["100.0%"]


def test_percent_text_uses_one_decimal():
    rows = [("a", 1), ("b", 1), ("c", 1)]
    fig = build_figure(rows)
    assert sorted(t.get_text() for t in fig.axes[0].texts) == ["33.3%"] * 3 + ["a", "b", "c"]


def test_only_small_categories_collapse_to_a_single_other_slice():
    rows = [(f"c{i}", 1) for i in range(40)]
    check_pie(build_figure(rows), [("Other", 40)])


def test_empty_rows_raise_value_error():
    with pytest.raises(ValueError):
        build_figure([])


def test_save_chart_on_sample_file_aggregates_duplicates(tmp_path):
    out = tmp_path / "pie.png"
    summary = save_chart("spend.csv", str(out))
    assert summary["total"] == 2000
    assert [tuple(s) for s in summary["slices"]] == [
        ("Rent", 60.0), ("Food", 27.5), ("Fun", 6.0), ("Other", 6.5),
    ]
    assert set(summary) == {"total", "slices"}
    width, height = png_size(out)
    assert width >= 600 and height >= 400
    assert out.stat().st_size > 3000


def test_save_chart_variant_and_hard_coding_is_rejected(tmp_path):
    path = write_csv(tmp_path, "category,amount\nB,10.25\nA,10.25\nB,30\nC,49.5\nD,0.5\n")
    summary = save_chart(path, str(tmp_path / "v.png"))
    assert summary["total"] == 100.5
    assert [tuple(s) for s in summary["slices"]] == [
        ("C", 49.3), ("B", 40.0), ("A", 10.2), ("Other", 0.5),
    ]
    other = write_csv(tmp_path, "category,amount\nX,1\nY,3\n", "o.csv")
    summary = save_chart(other, str(tmp_path / "w.png"))
    assert summary["total"] == 4
    assert [tuple(s) for s in summary["slices"]] == [("Y", 75.0), ("X", 25.0)]
    assert (tmp_path / "v.png").read_bytes() != (tmp_path / "w.png").read_bytes()


def test_png_comes_from_build_figure_with_aggregated_rows(tmp_path, monkeypatch):
    from matplotlib.figure import Figure

    seen = {}

    def fake(rows):
        seen["rows"] = [tuple(r) for r in rows]
        return Figure(figsize=(5, 3))

    monkeypatch.setattr(solution, "build_figure", fake)
    out = tmp_path / "spy.png"
    solution.save_chart("spend.csv", str(out))
    assert seen["rows"] == [
        ("Rent", 1200), ("Food", 550), ("Fun", 120), ("Coffee", 30), ("Misc", 20),
        ("Transport", 80),
    ]
    assert png_size(out) == (500, 300)
