import struct

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402

from solution import build_figure, save_chart  # noqa: E402

SIGNATURE = b"\x89PNG\r\n\x1a\n"
DEFAULT = [0, 20, 40, 60, 80, 100]


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


def check_hist(fig, counts, edges):
    assert len(fig.axes) == 1
    ax = fig.axes[0]
    assert ax.get_title() == "Exam Scores"
    assert ax.get_xlabel() == "Score"
    assert ax.get_ylabel() == "Students"
    assert tuple(fig.get_size_inches()) == pytest.approx((8, 4.5))
    bars = ax.patches
    assert [p.get_height() for p in bars] == pytest.approx(counts)
    assert [p.get_x() for p in bars] == pytest.approx(edges[:-1])
    assert [p.get_width() for p in bars] == pytest.approx(
        [b - a for a, b in zip(edges, edges[1:])])


def write_csv(tmp_path, text, name="in.csv"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_default_edges_and_counts():
    check_hist(build_figure([5, 25, 26, 45, 65, 66, 67, 85, 95]), [1, 2, 1, 3, 2], DEFAULT)


def test_values_on_edges_go_to_the_upper_bin_but_the_last_edge_is_inclusive():
    rows = [0, 20, 40, 60, 80, 100]
    check_hist(build_figure(rows), [1, 1, 1, 1, 2], DEFAULT)
    check_hist(build_figure([19.999, 39.999999, 99.99, 100.0]), [1, 1, 0, 0, 2], DEFAULT)


def test_values_outside_the_edges_are_ignored():
    check_hist(build_figure([-0.001, 100.001, -50, 1000, 50]), [0, 0, 1, 0, 0], DEFAULT)


def test_empty_bins_still_have_bars_and_empty_rows_are_allowed():
    check_hist(build_figure([]), [0, 0, 0, 0, 0], DEFAULT)
    check_hist(build_figure([90, 91]), [0, 0, 0, 0, 2], DEFAULT)


def test_custom_unequal_edges():
    rows = [1, 2, 9, 10, 10, 55, 60, 61, -1]
    check_hist(build_figure(rows, edges=[0, 10, 50, 60]), [3, 2, 2], [0, 10, 50, 60])
    check_hist(build_figure([1, 2, 2, 3], edges=[0.5, 1.5, 2.5]), [1, 2], [0.5, 1.5, 2.5])
    check_hist(build_figure([1, 2], [0, 5]), [2], [0, 5])


@pytest.mark.parametrize("edges", [[], [5], [10, 5], [1, 1, 2], [0, 5, 5], [0, 3, 2, 9]])
def test_bad_edges_raise_value_error(edges):
    with pytest.raises(ValueError):
        build_figure([1, 2, 3], edges=edges)


def test_save_chart_on_sample_file(tmp_path):
    out = tmp_path / "h.png"
    summary = save_chart("scores.csv", str(out))
    assert summary == {
        "counts": [1, 1, 2, 2, 3], "edges": DEFAULT, "outside": 2, "mean": 57.99,
    }
    assert all(isinstance(c, int) for c in summary["counts"])
    width, height = png_size(out)
    assert width >= 600 and height >= 300
    assert out.stat().st_size > 3000


def test_save_chart_variant_with_blank_scores(tmp_path):
    path = write_csv(tmp_path, "student,score\na,19.5\nb,\nc,20\nd,\ne,99\nf,100.5\n")
    out = tmp_path / "v.png"
    assert save_chart(path, str(out)) == {
        "counts": [1, 1, 0, 0, 1], "edges": DEFAULT, "outside": 1, "mean": 59.75,
    }
    assert png_size(out) == (800, 450)


def test_save_chart_without_scores(tmp_path):
    path = write_csv(tmp_path, "student,score\na,\nb, \n")
    summary = save_chart(path, str(tmp_path / "e.png"))
    assert summary == {"counts": [0, 0, 0, 0, 0], "edges": DEFAULT, "outside": 0, "mean": None}


def test_png_depends_on_the_data(tmp_path):
    a = write_csv(tmp_path, "student,score\na,10\nb,15\nc,90\n", "a.csv")
    b = write_csv(tmp_path, "student,score\na,50\nb,55\nc,58\nd,59\n", "b.csv")
    save_chart(a, str(tmp_path / "a.png"))
    save_chart(b, str(tmp_path / "b.png"))
    assert (tmp_path / "a.png").read_bytes() != (tmp_path / "b.png").read_bytes()
