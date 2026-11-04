import struct

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402

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


def check_content(fig, rows):
    assert len(fig.axes) == 1
    ax = fig.axes[0]
    assert ax.get_title() == "Daily Sales"
    assert ax.get_xlabel() == "Day"
    assert ax.get_ylabel() == "Units sold"
    assert len(ax.lines) == 2
    online, store = ax.lines
    assert list(online.get_xdata()) == [r[0] for r in rows]
    assert list(store.get_xdata()) == [r[0] for r in rows]
    assert list(online.get_ydata()) == pytest.approx([r[1] for r in rows])
    assert list(store.get_ydata()) == pytest.approx([r[2] for r in rows])
    assert [t.get_text() for t in ax.get_legend().get_texts()] == ["Online", "Store"]
    assert tuple(fig.get_size_inches()) == pytest.approx((8, 4.5))


def write_csv(tmp_path, text, name="in.csv"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_two_lines_with_data_labels_and_legend():
    rows = [(1, 10, 5.5), (2, 12, 7), (3, 9, 8.25)]
    fig = build_figure(rows)
    check_content(fig, rows)
    ax = fig.axes[0]
    assert ax.lines[0].get_label() == "Online"
    assert ax.lines[1].get_label() == "Store"


def test_other_rows_give_other_series_and_series_are_not_swapped():
    rows = [(10, 1, 100), (20, 2, 90), (30, 3, 80), (40, 4, 70)]
    check_content(build_figure(rows), rows)
    ax = build_figure([(5, 0, 50)]).axes[0]
    assert list(ax.lines[0].get_ydata()) == [0]
    assert list(ax.lines[1].get_ydata()) == [50]


def test_rows_are_plotted_in_given_order_not_sorted():
    rows = [(3, 1, 1), (1, 2, 2), (2, 3, 3)]
    ax = build_figure(rows).axes[0]
    assert list(ax.lines[0].get_xdata()) == [3, 1, 2]


def test_empty_rows_still_have_two_labelled_lines_and_legend():
    fig = build_figure([])
    ax = fig.axes[0]
    assert len(ax.lines) == 2
    assert [len(line.get_xdata()) for line in ax.lines] == [0, 0]
    assert [t.get_text() for t in ax.get_legend().get_texts()] == ["Online", "Store"]
    assert ax.get_title() == "Daily Sales"


def test_save_chart_on_sample_file_sorts_by_day(tmp_path):
    out = tmp_path / "c.png"
    summary = save_chart("sales.csv", str(out))
    assert summary == {
        "days": 5, "online_total": 695.5, "store_total": 487.5, "leader": "online",
    }
    width, height = png_size(out)
    assert width >= 600 and height >= 300
    assert out.stat().st_size > 3000


def test_leader_store_tie_and_rounding(tmp_path):
    path = write_csv(tmp_path, "day,online,store\n2,1.005,3\n1,2.004,4\n")
    s = save_chart(path, str(tmp_path / "a.png"))
    assert s["leader"] == "store"
    assert s["online_total"] == round(1.005 + 2.004, 2)
    assert s["store_total"] == 7.0
    path = write_csv(tmp_path, "day,online,store\n1,0.1,0.3\n2,0.2,0.0\n", "t.csv")
    s = save_chart(path, str(tmp_path / "b.png"))
    assert (s["online_total"], s["store_total"], s["leader"]) == (0.3, 0.3, "tie")


def test_save_chart_passes_sorted_rows_to_the_plot(tmp_path, monkeypatch):
    import solution

    seen = {}
    real = solution.build_figure

    def spy(rows):
        seen["rows"] = list(rows)
        return real(rows)

    monkeypatch.setattr(solution, "build_figure", spy)
    path = write_csv(tmp_path, "day,online,store\n10,1,1\n2,2,2\n7,3,3\n")
    solution.save_chart(path, str(tmp_path / "s.png"))
    assert [r[0] for r in seen["rows"]] == [2, 7, 10]
    assert [r[1] for r in seen["rows"]] == [2, 3, 1]


def test_png_depends_on_the_data(tmp_path):
    a = write_csv(tmp_path, "day,online,store\n1,1,2\n2,5,1\n", "a.csv")
    b = write_csv(tmp_path, "day,online,store\n1,9,2\n2,1,8\n", "b.csv")
    save_chart(a, str(tmp_path / "a.png"))
    save_chart(b, str(tmp_path / "b.png"))
    assert (tmp_path / "a.png").read_bytes() != (tmp_path / "b.png").read_bytes()
    assert png_size(tmp_path / "a.png") == png_size(tmp_path / "b.png") == (800, 450)


def test_single_day_file(tmp_path):
    path = write_csv(tmp_path, "day,online,store\n1,4,4\n")
    out = tmp_path / "one.png"
    assert save_chart(path, str(out)) == {
        "days": 1, "online_total": 4.0, "store_total": 4.0, "leader": "tie",
    }
    assert png_size(out) == (800, 450)
