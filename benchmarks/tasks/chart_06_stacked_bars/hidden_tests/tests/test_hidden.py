import io
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


def check_stack(fig, quarters, matrix):
    """matrix: {product: [units per quarter]}; products must be sorted ascending."""
    assert len(fig.axes) == 1
    ax = fig.axes[0]
    fig.savefig(io.BytesIO(), format="png")  # forces tick labels to be computed
    assert ax.get_title() == "Units by Quarter"
    assert ax.get_xlabel() == "Quarter"
    assert ax.get_ylabel() == "Units"
    assert tuple(fig.get_size_inches()) == pytest.approx((8, 5))
    products = list(matrix)
    assert products == sorted(products)
    assert [t.get_text() for t in ax.get_legend().get_texts()] == products
    assert [c.get_label() for c in ax.containers] == products
    assert [t.get_text() for t in ax.get_xticklabels()] == quarters
    below = [0.0] * len(quarters)
    for container, product in zip(ax.containers, products):
        bars = list(container)
        assert len(bars) == len(quarters)
        assert [b.get_height() for b in bars] == pytest.approx(matrix[product])
        assert [b.get_y() for b in bars] == pytest.approx(below)
        xs = [b.get_x() + b.get_width() / 2 for b in bars]
        assert xs == sorted(xs)
        below = [a + h for a, h in zip(below, matrix[product])]
    assert len(ax.patches) == len(products) * len(quarters)


def write_csv(tmp_path, text, name="in.csv"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_pivot_with_first_appearance_quarters_and_sorted_products():
    rows = [("Q2", "widget", 30), ("Q1", "widget", 10), ("Q1", "gadget", 25),
            ("Q2", "gizmo", 5), ("Q3", "gadget", 40)]
    check_stack(build_figure(rows), ["Q2", "Q1", "Q3"], {
        "gadget": [0, 25, 40], "gizmo": [5, 0, 0], "widget": [30, 10, 0],
    })


def test_duplicate_pairs_are_added_together():
    rows = [("A", "x", 1), ("A", "x", 2), ("B", "x", 4), ("A", "y", 10), ("A", "x", 0.5)]
    check_stack(build_figure(rows), ["A", "B"], {"x": [3.5, 4], "y": [10, 0]})


def test_other_data_other_chart_and_stack_order_follows_sorted_products():
    rows = [("2023", "zebra", 7), ("2023", "apple", 3), ("2024", "mango", 11),
            ("2024", "apple", 1), ("2022", "zebra", 2)]
    check_stack(build_figure(rows), ["2023", "2024", "2022"], {
        "apple": [3, 1, 0], "mango": [0, 11, 0], "zebra": [7, 0, 2],
    })


def test_single_row_and_single_product():
    check_stack(build_figure([("Only", "p", 9)]), ["Only"], {"p": [9]})
    check_stack(build_figure([("B", "p", 1), ("A", "p", 2)]), ["B", "A"], {"p": [1, 2]})


def test_product_names_sort_in_plain_string_order():
    rows = [("Q", "b", 1), ("Q", "B", 2), ("Q", "a", 3), ("Q", "10", 4), ("Q", "9", 5)]
    fig = build_figure(rows)
    assert [c.get_label() for c in fig.axes[0].containers] == ["10", "9", "B", "a", "b"]


def test_empty_rows_raise_value_error():
    with pytest.raises(ValueError):
        build_figure([])


def test_save_chart_on_sample_file(tmp_path):
    out = tmp_path / "s.png"
    summary = save_chart("units.csv", str(out))
    assert summary == {
        "quarters": ["Q2", "Q1", "Q3"], "products": ["gadget", "gizmo", "widget"],
        "totals": [35, 40, 40], "top_product": "gadget",
    }
    assert all(isinstance(t, int) for t in summary["totals"])
    width, height = png_size(out)
    assert width >= 600 and height >= 400
    assert out.stat().st_size > 3000


def test_top_product_ties_pick_the_first_sorted_product(tmp_path):
    path = write_csv(tmp_path, "quarter,product,units\nQ1,pear,5\nQ1,apple,2\nQ2,apple,3\n"
                               "Q2,cherry,5\nQ2,cherry,0\n")
    summary = save_chart(path, str(tmp_path / "t.png"))
    assert summary["products"] == ["apple", "cherry", "pear"]
    assert summary["top_product"] == "apple"
    assert summary["totals"] == [7, 8]
    path = write_csv(tmp_path, "quarter,product,units\nQ1,zeta,9\nQ1,beta,1\n", "u.csv")
    assert save_chart(path, str(tmp_path / "u.png"))["top_product"] == "zeta"


def test_save_chart_passes_file_order_rows(tmp_path, monkeypatch):
    import solution

    seen = {}
    real = solution.build_figure

    def spy(rows):
        seen["rows"] = [tuple(r) for r in rows]
        return real(rows)

    monkeypatch.setattr(solution, "build_figure", spy)
    path = write_csv(tmp_path, "quarter,product,units\nB,x,1\nA,y,2\nB,y,3\n")
    summary = solution.save_chart(path, str(tmp_path / "f.png"))
    assert seen["rows"] == [("B", "x", 1), ("A", "y", 2), ("B", "y", 3)]
    assert summary["quarters"] == ["B", "A"]
    assert summary["totals"] == [4, 2]


def test_png_depends_on_the_data(tmp_path):
    a = write_csv(tmp_path, "quarter,product,units\nQ1,a,1\nQ2,a,9\n", "a.csv")
    b = write_csv(tmp_path, "quarter,product,units\nQ1,a,9\nQ1,b,4\nQ2,b,1\n", "b.csv")
    save_chart(a, str(tmp_path / "a.png"))
    save_chart(b, str(tmp_path / "b.png"))
    assert (tmp_path / "a.png").read_bytes() != (tmp_path / "b.png").read_bytes()
    assert png_size(tmp_path / "a.png") == png_size(tmp_path / "b.png") == (800, 500)
