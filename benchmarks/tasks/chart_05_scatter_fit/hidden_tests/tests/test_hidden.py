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


def least_squares(rows):
    """Independent closed form: normal equations with raw sums."""
    n = len(rows)
    sx = sum(x for x, _ in rows)
    sy = sum(y for _, y in rows)
    sxx = sum(x * x for x, _ in rows)
    sxy = sum(x * y for x, y in rows)
    slope = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    return slope, (sy - slope * sx) / n


def check_scatter(fig, rows):
    assert len(fig.axes) == 1
    ax = fig.axes[0]
    assert ax.get_title() == "Study Hours vs Exam Score"
    assert ax.get_xlabel() == "Hours studied"
    assert ax.get_ylabel() == "Exam score"
    assert tuple(fig.get_size_inches()) == pytest.approx((7, 5))
    assert len(ax.collections) == 1 and len(ax.lines) == 1
    offsets = ax.collections[0].get_offsets()
    assert len(offsets) == len(rows)
    assert [float(v) for p in offsets for v in p] == pytest.approx(
        [float(v) for r in rows for v in r])
    slope, intercept = least_squares(rows)
    xs = [x for x, _ in rows]
    line = ax.lines[0]
    assert list(line.get_xdata()) == pytest.approx([min(xs), max(xs)])
    assert list(line.get_ydata()) == pytest.approx(
        [slope * min(xs) + intercept, slope * max(xs) + intercept])
    assert [t.get_text() for t in ax.get_legend().get_texts()] == ["Data", "Fit"]
    assert ax.collections[0].get_label() == "Data" and line.get_label() == "Fit"


def write_csv(tmp_path, text, name="in.csv"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_scatter_points_in_row_order_and_fit_line_ends():
    rows = [(3.0, 61.0), (1.0, 52.0), (6.0, 71.0), (2.0, 55.0), (5.0, 70.0), (4.0, 64.0)]
    check_scatter(build_figure(rows), rows)


def test_decreasing_trend_and_other_data():
    rows = [(10.0, 5.0), (0.0, 9.5), (4.0, 7.0), (-2.0, 11.0), (7.0, 4.0)]
    check_scatter(build_figure(rows), rows)
    rows = [(1, 1), (2, 3)]
    check_scatter(build_figure(rows), rows)


def test_fit_line_is_not_through_the_origin_or_the_mean_only():
    rows = [(100.0, 1000.0), (200.0, 1010.0), (300.0, 1035.0), (150.0, 1002.0)]
    ax = build_figure(rows).axes[0]
    slope, intercept = least_squares(rows)
    assert list(ax.lines[0].get_ydata()) == pytest.approx([slope * 100 + intercept,
                                                           slope * 300 + intercept])
    assert intercept == pytest.approx(ax.lines[0].get_ydata()[0] - slope * 100)


@pytest.mark.parametrize("rows", [[], [(1, 2)], [(2, 1), (2, 5), (2, 9)]])
def test_degenerate_data_raises_value_error(rows):
    with pytest.raises(ValueError):
        build_figure(rows)


def test_save_chart_on_sample_file(tmp_path):
    out = tmp_path / "s.png"
    summary = save_chart("study.csv", str(out))
    assert summary == {"n": 6, "slope": 4.086, "intercept": 47.867, "r_squared": 0.978}
    assert isinstance(summary["n"], int)
    width, height = png_size(out)
    assert width >= 600 and height >= 400
    assert out.stat().st_size > 3000


def test_save_chart_passes_rows_in_file_order_skipping_incomplete_rows(tmp_path, monkeypatch):
    seen = {}
    real = solution.build_figure

    def spy(rows):
        seen["rows"] = [tuple(r) for r in rows]
        return real(rows)

    monkeypatch.setattr(solution, "build_figure", spy)
    path = write_csv(tmp_path, "hours,score\n5,2\n,3\n1,\n9,8\n2,4\n")
    summary = solution.save_chart(path, str(tmp_path / "f.png"))
    assert seen["rows"] == [(5.0, 2.0), (9.0, 8.0), (2.0, 4.0)]
    assert summary["n"] == 3


def test_perfect_negative_line(tmp_path):
    path = write_csv(tmp_path, "hours,score\n0,10\n1,8\n2,6\n5,0\n")
    out = tmp_path / "n.png"
    assert save_chart(path, str(out)) == {
        "n": 4, "slope": -2.0, "intercept": 10.0, "r_squared": 1.0,
    }
    assert png_size(out)[0] >= 600


def test_constant_scores_give_r_squared_one(tmp_path):
    path = write_csv(tmp_path, "hours,score\n1,7\n2,7\n9,7\n")
    summary = save_chart(path, str(tmp_path / "c.png"))
    assert summary == {"n": 3, "slope": 0.0, "intercept": 7.0, "r_squared": 1.0}


def test_noisy_data_has_lower_r_squared(tmp_path):
    path = write_csv(tmp_path, "hours,score\n1,10\n2,2\n3,9\n4,3\n5,8\n")
    s = save_chart(path, str(tmp_path / "z.png"))
    # by hand: mean_x=3, mean_y=6.4, Sxx=10, Sxy=-3, SStot=51.8 -> r2 = 0.9 / 51.8
    assert (s["slope"], s["intercept"]) == (-0.3, 7.3)
    assert s["r_squared"] == 0.017


def test_save_chart_errors_propagate_for_degenerate_files(tmp_path):
    for body in ("hours,score\n", "hours,score\n1,2\n", "hours,score\n3,1\n3,5\n"):
        path = write_csv(tmp_path, body)
        with pytest.raises(ValueError):
            save_chart(path, str(tmp_path / "x.png"))


def test_png_depends_on_the_data(tmp_path):
    a = write_csv(tmp_path, "hours,score\n1,1\n2,2\n3,3.5\n", "a.csv")
    b = write_csv(tmp_path, "hours,score\n1,5\n2,2\n3,1\n", "b.csv")
    save_chart(a, str(tmp_path / "a.png"))
    save_chart(b, str(tmp_path / "b.png"))
    assert (tmp_path / "a.png").read_bytes() != (tmp_path / "b.png").read_bytes()


def test_r_squared_comes_from_the_unrounded_fit(tmp_path):
    # slope 0.0007 and intercept 100.0023 rounded first would give r2 0.053, not 0.119
    path = write_csv(
        tmp_path, "hours,score\n1,100.0\n2,100.007\n3,100.004\n4,100.008\n5,100.003\n")
    s = save_chart(path, str(tmp_path / "r.png"))
    assert s == {"n": 5, "slope": 0.001, "intercept": 100.002, "r_squared": 0.119}


def test_whitespace_only_cells_are_skipped(tmp_path):
    path = write_csv(tmp_path, "hours,score\n1,2\n 2, \n  ,5\n3,6\n")
    summary = save_chart(path, str(tmp_path / "w.png"))
    assert summary == {"n": 2, "slope": 2.0, "intercept": 0.0, "r_squared": 1.0}
