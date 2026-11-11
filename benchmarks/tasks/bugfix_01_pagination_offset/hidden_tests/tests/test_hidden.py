import pytest

from pagination import get_page, page_count

ITEMS = list(range(1, 26))


def test_first_page_holds_the_first_items():
    assert get_page(ITEMS, 1, 10) == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]


def test_last_page_may_be_shorter():
    assert get_page(ITEMS, 3, 10) == [21, 22, 23, 24, 25]


def test_default_page_size_is_ten():
    assert get_page(ITEMS, 2) == list(range(11, 21))


def test_pages_cover_every_item_exactly_once():
    letters = list("abcdefghijklmnopq")
    for per_page in (1, 4, 5, 17, 20):
        pages = [get_page(letters, n, per_page) for n in range(1, page_count(17, per_page) + 1)]
        assert [x for page in pages for x in page] == letters


def test_page_past_the_end_is_empty():
    assert get_page(ITEMS, 4, 10) == []
    assert get_page(ITEMS, 99, 10) == []
    assert get_page([], 1, 10) == []
    assert get_page(list("abc"), 2, 3) == []


def test_invalid_arguments_raise_value_error():
    for page, per_page in ((0, 10), (-1, 10), (1, 0), (1, -5)):
        with pytest.raises(ValueError):
            get_page(ITEMS, page, per_page)


def test_returns_new_list_and_leaves_items_alone():
    items = list("abcdef")
    page = get_page(items, 1, 6)
    assert page == list("abcdef")
    assert page is not items
    page.append("z")
    assert items == list("abcdef")


def test_page_count_is_unchanged():
    assert page_count(0, 10) == 0
    assert page_count(1, 10) == 1
    assert page_count(25, 10) == 3
    assert page_count(30, 10) == 3
    with pytest.raises(ValueError):
        page_count(5, 0)
